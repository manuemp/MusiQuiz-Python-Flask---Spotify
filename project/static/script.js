if (document.getElementById("results"))
{
    var redirect = window.location.href.replace("/artistResults","/");
    var redir_counter = 0
    var correct_answer;
    var user_answer;
    var success;
    var cont
    cont = 1

    while ( document.getElementById(`answer${cont}`) && document.getElementById(`user_answer${cont}`)  )
    {
        correct_answer = document.getElementById(`answer${cont}`);
        user_answer = document.getElementById(`user_answer${cont}`);

        if (correct_answer.innerHTML == user_answer.innerHTML)
        {
            user_answer.style.backgroundColor = "#49a078";
        }
        else
        {
            user_answer.style.backgroundColor = "red";
        }
        cont = cont + 1;
    }


    if ( window.history.replaceState ) {
        redir_counter = redir_counter + 1;
        window.history.replaceState( null, null, window.location.href );
        if (redir_counter > 1)
        {
            window.location.replace(redirect);
        }
    }
}

if (document.getElementById("artistQuiz"))
{

    var sliders = document.querySelectorAll(".slide-form");
    var prev = document.querySelector(".prev-button");
    var next = document.querySelector(".next-button");
    var identifier = 1;

    if (identifier == 1){
        prev.style.display = "none";
    }
    
    sliders.forEach( slide =>{
        if (slide.id != identifier) {
            slide.style.display = "none";
        }
        else{
            slide.style.display = "block";
        }
    })
    
    prev.addEventListener("click", ev=>{

        if( identifier == 2 ){
            prev.style.display = "none";
            console.log("limit")
        }

        if (identifier == 8){
            next.style.display = "block";
        }

        if (identifier > 1)
        {
            identifier = identifier - 1;
            console.log("clicked prev")
            console.log(identifier)
        }
        sliders.forEach( slide =>{
            if (slide.id != identifier) {
                slide.style.display = "none";
            }
            else{
                slide.style.display = "block";
            }
        })
    })
    
    next.addEventListener("click", ev=>{

        if (identifier == 1){
            prev.style.display = "block";
        }

        if (identifier == 7){
            next.style.display = "none";
        }

        identifier = identifier + 1;
        console.log(identifier)
        sliders.forEach( slide =>{
            if (slide.id != identifier) {
                slide.style.display = "none";
            }
            else{
                slide.style.display = "block";
            }
        })
    })
}

if (document.querySelector(".bg-success")){
    success = document.querySelector(".bg-success");
    success.style.width = `${success.innerHTML}`;
}

// In case there are more than one
if (document.querySelectorAll(".bg-success")){
    success_bars = document.querySelectorAll(".bg-success");
    success_bars.forEach( bar =>{
        bar.style.width = `${bar.innerHTML}`;
    } )

}

// if (document.getElementById("stats")){

//     var stats_menu = document.getElementById("stats")
//     var stats_link = document.getElementById("stats-link")
//     var main = document.getElementById("main")
//     var counter = 0

//     stats_link.addEventListener("click", ev => {
//         counter = counter + 1;

//         if (counter == 1){
//             stats_menu.style.visibility = "visible";
//             stats_menu.style.opacity = 1;
//         }
//         if (counter > 1){
//             stats_menu.style.visibility = "hidden";
//             stats_menu.style.opacity = 0;
//             counter = 0;
//         }
//     })

//     main.addEventListener("click", ev => {
//         stats_menu.style.visibility = "hidden";
//         stats_menu.style.opacity = 0;
//         counter = 0;
//     })

// }


