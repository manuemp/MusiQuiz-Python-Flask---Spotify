from flask import Flask, request, url_for, session, redirect, render_template
import sqlite3
import time
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import re

app = Flask(__name__)

# La clave secreta se usa para la cookie de la sesión 
# En el video escribe cualquier cosa manualmente
app.secret_key = "aoJpK3_aky82e"
app.config['SESSION_COOKIE_NAME'] = 'App Cookie'

#################################################################
# FUNCTIONS 
#################################################################

def get_token():
    # Search for the token_info cookie, if not found return None
    token_info = session.get("token_info", None)

    if not token_info:
        raise "Token not found!"
    
    now = time.time()
    # If session is about to expire
    is_expired = token_info['expires_at'] - now < 60
    
    if is_expired:
        # Create an oauth and refresh access token
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])

    return token_info


def get_rand_array(length, limit):
    arr = []
    while len(arr) < limit:
        num = random.randint(0, length)
        if not num in arr:
            arr.append(num)
    return arr
    

def get_max_counter(arr):
    max = 0
    indx = 0
    for i in range(0, 4):
        num = str(arr[i][1]).replace(",","")
        num = int(num)
        if num > max:
            max = num
            indx = i
    return indx

def get_quiz_results(dict1, dict2, len):
    # Correct Answers -> array[0], Incorrect answers -> array[1]
    array = [0, 0]
    for i in range(0, len):
        if str(dict2[f"q{i+1}"]) == str(dict1[f"q{i+1}"]):
            array[0] += 1
        else:
            array[1] += 1
    return array

def sql_submit(username, id, correct_answers, wrong_answers, total_questions, db):
        
        database = sqlite3.connect("quiz.db")
        cur = database.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {db} (
                    id VARCHAR PRIMARY KEY,
                    username VARCHAR, 
                    correct_answers INTEGER,
                    wrong_answers INTEGER,
                    total INTEGER,
                    average REAL,
                    game_count INTEGER
                    ); """)

        user_verify = cur.execute(f"SELECT * FROM {db} WHERE id = (?)", (id,)).fetchall()

        if (len(user_verify) == 0):
            cur.execute(f"INSERT INTO {db} VALUES (?, ?, 0, 0, 0, 0, 0)", (id, username)) 
            database.commit()

        cur.execute(f"""UPDATE {db} SET correct_answers = correct_answers + ?, 
            wrong_answers = wrong_answers + ?,
            total = total + ?,
            game_count = game_count + 1
            WHERE id = ?""", (correct_answers, wrong_answers, total_questions, id,))
        cur.execute(f"""UPDATE {db} SET average = ROUND(((correct_answers*1.0 / total) * 100), 2)
                    WHERE id = ? """, (id,))

        sql_data = list(cur.execute(f"SELECT * FROM {db} WHERE id = ?", (id,)).fetchall())
        database.commit()
        cur.close()

        return sql_data


#################################################################
#GLOBAL DICTS
#################################################################
          
# DICT FOR QUIZ ANSWERS
correct_answers = {}
# DICT FOR ArtistQuiz RESULTS
results_titles_dict = {}

#################################################################
#ROUTES
#################################################################


@app.route("/redirect")
def redirectPage():

    # Each time the API is used, authorization is needed
    sp_oauth = create_spotify_oauth()
    session.clear() 
    code = request.args.get("code")
    # token_info will contain the access token
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info

    return redirect(url_for("search", _external= True))


@app.route("/login")
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/")
def index():

    try:
        get_token()
    except:
        session.clear()
        return redirect("/info") 

    return redirect("/search")   


@app.route("/logout")
def logout():
    session.clear()
    return redirect ('https://www.spotify.com/logout/')


@app.route("/search", methods=["GET", "POST"])
def search():

    try:
        get_token()
    except:
        session.clear()
        return redirect("/login")

    if request.method != "POST":
        return render_template("search.html")
    else:
        return redirect("/artistQuiz")


@app.route("/stats")
def stats():

    try:
        token_info = get_token()
    except:
        session.clear()
        return redirect("/login")    

    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_id = str(sp.current_user()["id"])

    database = sqlite3.connect("quiz.db")
    cur = database.cursor()

    artistquiz = list(cur.execute("SELECT * FROM artistQuiz WHERE id = ?", (user_id,)).fetchall())
    listenersquiz = list(cur.execute("SELECT * FROM listenersQuiz WHERE id = ?", (user_id,)).fetchall())
    streamsquiz = list(cur.execute("SELECT * FROM streamsQuiz WHERE id = ?", (user_id,)).fetchall())
    total_dict = {
        "total_count": artistquiz[0][4] + listenersquiz[0][4] + streamsquiz[0][4],
        "total_corrects": artistquiz[0][2] + listenersquiz[0][2] + streamsquiz[0][2],
        "total_attempts": artistquiz[0][6] + listenersquiz[0][6] + streamsquiz[0][6],
        "total_avg": round((artistquiz[0][2] + listenersquiz[0][2] + streamsquiz[0][2]) / (artistquiz[0][4] + listenersquiz[0][4] + streamsquiz[0][4])*100, 2)
    }

    return render_template("stats.html", artistquiz=artistquiz, listenersquiz=listenersquiz, streamsquiz = streamsquiz, total_dict=total_dict)


@app.route("/info", methods=["GET"])
def info():
    try:
        get_token()
    except:
        session.clear()
        return render_template("info-offline.html")

    return render_template("info.html")


@app.route("/artistQuiz", methods=["GET", "POST"])
def artistQuiz():
    # Check if token is not expired
    try:
        token_info = get_token()
    except:
        print("User not logged in")
        session.clear()
        return redirect("/login")
        # return redirect ('https://www.spotify.com/logout/')

    def get_random_tracks(id):
        album = sp.album_tracks(album_id=id)
        length = len(album) - 1
        return album["items"][random.randint(0,length)]["name"]
    
    # Not allow to enter directly from URL
    if request.method == "GET":
        return redirect("/search")

    # Clear the global correct_answers dict and get access Token to allow connection to Spotify API
    correct_answers.clear()
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # Get data from API
    try:
        searched_artist = request.form.get("search_artist")
        artist = sp.search(searched_artist, type="artist", limit= 1)
        name = artist["artists"]["items"][0]["name"]
        id_artist = str(artist["artists"]["items"][0]["id"])

        albums = sp.artist_albums(artist_id=id_artist)
        songs = sp.artist_top_tracks(id_artist)
        img = artist["artists"]["items"][0]["images"][0]["url"]
        top_song = songs["tracks"][0]["name"]
        follows = artist["artists"]["items"][0]["followers"]["total"]


        # Get a list with albums only, avoiding compilations, singles, EP's
        # or duplications (sometimes there are)
        album_list = []
        for i in range(0, len(albums["items"])):
            flag = 0
            if albums["items"][i]["album_type"] == "album":
                for j in range(0, len(album_list)):
                    if albums["items"][i]["name"] == album_list[j]["name"]:
                        flag = 1
                        break
                if not flag:
                    album_list.append(albums["items"][i])
                else:
                    continue

        # If the album list does not have at least 4 albums, redirect
        if len(album_list) < 4:
            return render_template("error.html"), {"Refresh": "4; /search"}

        # Question 1
        # 'follows' is the variable with the correct amount of followers, then 3 random options
        # are created
        
        followers = [follows, random.randint(int(follows * 0.5), int(follows * 1.5)), 
                random.randint(int(follows * 0.5), int(follows * 1.5)),
                random.randint(int(follows * 0.5), int(follows * 1.5))
                ]
        # Alter order
        random.shuffle(followers)

        # All the 'random.shuffle()' lines will alter randomly the order of the array with
        # the options for each question, to put the correct question in a different place 
        # each attempt, making the quiz not predictable 

        # Question 2
        top_songs = []
        # Get the top 4 songs according to the API
        for i in range(0, 4):
            top_songs.append(songs["tracks"][i]["name"])
        # Alter order
        random.shuffle(top_songs)
        
        # Get random indexes for questions.
        album_indexes_1 = get_rand_array(len(album_list) - 1, 4)
        album_indexes_2 = get_rand_array(len(album_list) - 1, 4)
        
        # An array of dicts for each question
        questions_dict = []

        #Question 3
        questions_dict.append({
                "name" : album_list[album_indexes_1[0]]["name"], 
                "year" : album_list[album_indexes_1[0]]["release_date"][:4],
                "img"  : album_list[album_indexes_1[0]]["images"][0]["url"] 
            })

        #Question 4
        questions_dict.append({
                "name" : album_list[album_indexes_1[1]]["name"], 
                "total_tracks" : album_list[album_indexes_1[1]]["total_tracks"],
                "img"  : album_list[album_indexes_1[1]]["images"][0]["url"] 
        })

        # Question 5
        rand_tracks = []
        # Since the numbers in album_indexes are random and cannot be predicted, 
        # the answer track has to be set manually in a variable (answer_track), 
        # which in this case will be the array's [2] index 
        answer_track = get_random_tracks(album_list[album_indexes_1[2]]["id"])
        rand_tracks.append(answer_track)
        
        # For the rest of the albums in the array, get a random track of each one
        for i in album_indexes_1:
            # Avoid [2] index, else you're getting another random track for the same album
            if i == album_indexes_1[2]:
                continue
            track = get_random_tracks(album_list[i]["id"])
            rand_tracks.append(track)
        # Alter order
        random.shuffle(rand_tracks)

        questions_dict.append({
                "name" : album_list[album_indexes_1[2]]["name"], 
                "track" : answer_track,
                "tracks" : rand_tracks
        })

        # Question 4
        questions_dict.append({
                "name" : album_list[album_indexes_1[3]]["name"],
                "img"  : album_list[album_indexes_1[3]]["images"][0]["url"],
                "track" : get_random_tracks(album_list[album_indexes_1[3]]["id"]),
                "albums" : [album_list[album_indexes_1[0]]["name"], album_list[album_indexes_1[1]]["name"], 
                            album_list[album_indexes_1[2]]["name"], album_list[album_indexes_1[3]]["name"]]
        })

        # Question 5
        questions_dict.append({
                "name" : album_list[album_indexes_2[0]]["name"],
                "track" : get_random_tracks(album_list[album_indexes_2[0]]["id"]),
                "albums" : [album_list[album_indexes_2[0]]["name"], album_list[album_indexes_2[1]]["name"], 
                            album_list[album_indexes_2[2]]["name"], album_list[album_indexes_2[3]]["name"]]
        })

        # Get one of the first 3 related artists
        related_artist = sp.artist_related_artists(artist_id=id_artist)
        related_indx = random.randint(0, 3)
        related_dict = {
            "name" : related_artist["artists"][related_indx]["name"],
            "id" :  related_artist["artists"][related_indx]["id"],
            "followers" : related_artist["artists"][related_indx]["followers"]["total"]
        }
        # Check if the original aritst or the related artist has more followers
        answer_related = name if int(follows) > int(related_dict["followers"]) else related_dict["name"] 

        # SET QUESTIONS IN GLOBAL DICT
        results_titles_dict["name"] = name
        results_titles_dict["q3"] = questions_dict[0]["name"]
        results_titles_dict["q4"] = questions_dict[1]["name"]
        results_titles_dict["q5"] = questions_dict[2]["name"]
        results_titles_dict["q6"] = questions_dict[3]["track"]
        results_titles_dict["q7"] = questions_dict[4]["track"]

        # SET CORRECT ANSWERS IN THE GLOBAL DICT
        correct_answers["q1"] = follows
        correct_answers["q2"] = top_song
        correct_answers["q3"] = questions_dict[0]["year"]
        correct_answers["q4"] = questions_dict[1]["total_tracks"]
        correct_answers["q5"] = questions_dict[2]["track"]
        correct_answers["q6"] = questions_dict[3]["albums"][3]
        correct_answers["q7"] = questions_dict[4]["albums"][0]
        correct_answers["q8"] = answer_related

        random.shuffle(questions_dict[3]["albums"])
        random.shuffle(questions_dict[4]["albums"])

    # In case there is an error (non existing artist or not enough albums)
    except:
        return render_template("error.html"), {"Refresh": "4; /search"}
        
    return render_template("artistQuiz.html", img=img, name=name, followers=followers, top_songs=top_songs, questions_dict=questions_dict, related_dict=related_dict)


@app.route("/artistResults", methods=["GET", "POST"])
def artistResults():
    if request.method == "GET":
        return redirect("/search")
    else:
        try:
            token_info = get_token()
        except:
            print("User not logged in")
            session.clear()
            return redirect("/login")

        sp = spotipy.Spotify(auth=token_info['access_token'])

        user_answers = {}
        user_answers["q1"] = request.form.get("radio1")
        user_answers["q2"] = request.form.get("radio2")
        user_answers["q3"] = request.form.get("input-1")
        user_answers["q4"] = request.form.get("input-2")
        user_answers["q5"] = request.form.get("radio3")
        user_answers["q6"] = request.form.get("radio4")
        user_answers["q7"] = request.form.get("radio5")
        user_answers["q8"] = request.form.get("radio6")

        username = str(sp.current_user()["display_name"])
        user_id = str(sp.current_user()["id"])
        sql_results = get_quiz_results(user_answers, correct_answers, 8)
        sql_data = sql_submit(username, user_id, sql_results[0], sql_results[1], 8, "artistQuiz")

    return render_template("artistResults.html", correct_answers=correct_answers, user_answers=user_answers, sql_data=sql_data, results_titles_dict=results_titles_dict)


@app.route("/streamsQuiz", methods=["GET", "POST"])
def streamsQuiz():

    try:
        token_info = get_token()
    except:
        print("User not logged in")
        session.clear()
        return redirect("/login")

    sp = spotipy.Spotify(auth=token_info['access_token'])

    if request.method == "GET":

        correct_answers.clear()
        headers = {'Content-type': 'charset=utf-8'}

        # Because CORS was not allowed on this page, Ajax petitions could not be done.
        # Getting the page's HTML and filtering it with regex was my solution to get the data
        r = requests.get("https://kworb.net/spotify/artists.html", headers=headers, stream=True)
        r = r.iter_lines()
        # Since iter lines returns bytes, string must be a byte to avoid using
        # multiple times the str() function on each iteration
        string = b""

        # Translate iter_object bytes into fragments of string to apply the regex
        for i in r:
            string += i
        reg = """html">([\d\w\s]*)<\/a><\/div><\/td><td>(\d*,*\d*,\d*,\d*)<\/td>"""

        # Search for matches: 
        # Regex is grouped, therefore matches can be assigned 
        # in different variables (artist, count)
        response_array = []
        for artist, count in re.findall(reg, str(string, 'utf-8')):
            response_array.append((artist, count))
        
        artists = get_rand_array(150, 20)
        trivia_dicts = [
            {
                "name" : response_array[artists[0]][0],
                "counter":  response_array[artists[0]][1],
                "options": [response_array[artists[0]], response_array[artists[1]],response_array[artists[2]], response_array[artists[3]]]
            },
            {
                "name" : response_array[artists[4]][0],
                "counter":  response_array[artists[4]][1],
                "options": [response_array[artists[4]], response_array[artists[5]],response_array[artists[6]], response_array[artists[7]]]
            },
            {
                "name" : response_array[artists[8]][0],
                "counter":  response_array[artists[8]][1],
                "options": [response_array[artists[8]], response_array[artists[9]],response_array[artists[10]], response_array[artists[11]]]
            },
            {
                "name" : response_array[artists[12]][0],
                "counter":  response_array[artists[12]][1],
                "options": [response_array[artists[12]], response_array[artists[13]],response_array[artists[14]], response_array[artists[15]]]
            },
            {
                "name" : response_array[artists[16]][0],
                "counter":  response_array[artists[16]][1],
                "options": [response_array[artists[16]], response_array[artists[17]],response_array[artists[18]], response_array[artists[19]]]
            }
        ]

        # Get name of each group's most listened artist and set as correct answer
        for i in range(0, 5):
            correct = get_max_counter(trivia_dicts[i]["options"])
            correct_answers[f"q{i+1}"] = trivia_dicts[i]["options"][correct][0]

        # Alter order of all the options arrays
        for i in range(0, 4):
            random.shuffle(trivia_dicts[i]["options"])

        return render_template("streamQuiz.html", trivia_dicts=trivia_dicts)

    else:
        user_answers = {}
        user_answers["q1"] = request.form.get("radio1")
        user_answers["q2"] = request.form.get("radio2")
        user_answers["q3"] = request.form.get("radio3")
        user_answers["q4"] = request.form.get("radio4")
        user_answers["q5"] = request.form.get("radio5")

        username = str(sp.current_user()["display_name"])
        user_id = str(sp.current_user()["id"])
        sql_results = get_quiz_results(user_answers, correct_answers, 5)
        sql_data = sql_submit(username, user_id, sql_results[0], sql_results[1], 5, "streamsQuiz")
        quizname = "StreamsQuiz"

        return render_template("streamQuizResults.html", correct_answers=correct_answers, user_answers=user_answers, sql_data=sql_data, quizname=quizname)


@app.route("/listenersQuiz", methods=["GET", "POST"])
def listenersQuiz():
    try:
        token_info = get_token()
    except:
        print("User not logged in")
        session.clear()
        return redirect("/login")

    sp = spotipy.Spotify(auth=token_info['access_token'])

    if request.method == "GET":

        correct_answers.clear()

        r = requests.get("https://kworb.net/spotify/listeners.html")
        r = r.iter_lines()
        string = b""
        for i in r:
            string += i
        
        reg = """html">([\d\w\s]*)<\/a><\/div><\/td><td>(\d*,*\d*,\d*,\d*)<\/td>"""
        response_array = []
        for artist, listeners in re.findall(reg, str(string, 'utf-8')):
            response_array.append((artist, listeners))

        artists = get_rand_array(150, 20)
        trivia_dicts = [
            {
                "name" : response_array[artists[0]][0],
                "counter":  response_array[artists[0]][1],
                "options": [response_array[artists[0]], response_array[artists[1]],response_array[artists[2]], response_array[artists[3]]]
            },
            {
                "name" : response_array[artists[4]][0],
                "counter":  response_array[artists[4]][1],
                "options": [response_array[artists[4]], response_array[artists[5]],response_array[artists[6]], response_array[artists[7]]]
            },
            {
                "name" : response_array[artists[8]][0],
                "counter":  response_array[artists[8]][1],
                "options": [response_array[artists[8]], response_array[artists[9]],response_array[artists[10]], response_array[artists[11]]]
            },
            {
                "name" : response_array[artists[12]][0],
                "counter":  response_array[artists[12]][1],
                "options": [response_array[artists[12]], response_array[artists[13]],response_array[artists[14]], response_array[artists[15]]]
            },
            {
                "name" : response_array[artists[16]][0],
                "counter":  response_array[artists[16]][1],
                "options": [response_array[artists[16]], response_array[artists[17]],response_array[artists[18]], response_array[artists[19]]]
            }
        ]

        for i in range(0, 5):
            correct = get_max_counter(trivia_dicts[i]["options"])
            correct_answers[f"q{i+1}"] = trivia_dicts[i]["options"][correct][0]

        for i in range(0, 4):
            random.shuffle(trivia_dicts[i]["options"])

        return render_template("listenersQuiz.html", trivia_dicts=trivia_dicts)

    else:
        user_answers = {}
        user_answers["q1"] = request.form.get("radio1")
        user_answers["q2"] = request.form.get("radio2")
        user_answers["q3"] = request.form.get("radio3")
        user_answers["q4"] = request.form.get("radio4")
        user_answers["q5"] = request.form.get("radio5")

        username = str(sp.current_user()["display_name"])
        user_id = str(sp.current_user()["id"])
        sql_results = get_quiz_results(user_answers, correct_answers, 5)
        sql_data = sql_submit(username, user_id, sql_results[0], sql_results[1], 5, "listenersQuiz")
        quizname = "ListenersQuiz"
        print(sql_data)

        return render_template("streamQuizResults.html", correct_answers=correct_answers, user_answers=user_answers, sql_data=sql_data, quizname=quizname)


# Spotify authorization to use API
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id="3474a9b8fa164aeaa5cea66d44a16818",
        client_secret="feefa5ada6c542f7bfc51b403c2b4b2e",
        # To avoid typing localhost:5000/redirect, use url_for
        redirect_uri= url_for("redirectPage", _external= True),
        scope= "user-library-read")


#################################################################
# TESTS
#################################################################


@app.route("/home")
def home():
        try:
            token_info = get_token()
        except:
            print("User not logged in")
            session.clear()
            return redirect ('https://www.spotify.com/logout/')

        sp = spotipy.Spotify(auth=token_info['access_token'])
        artist = sp.artist("4LLpKhyESsyAXpc4laK94U")
        albums = sp.artist_albums(artist_id="4LLpKhyESsyAXpc4laK94U")

        return albums["items"][0]["name"]
