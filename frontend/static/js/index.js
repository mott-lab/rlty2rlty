let current_id = "";
let interrupt = false;
let first_count = true;

// var cfg_slider = document.getElementById("cfg_slider");
// var output = document.getElementById("cfg_value");
// output.innerHTML = cfg_slider.value; // Display the default slider value

// // Update the current slider value (each time you drag the slider handle)
// cfg_slider.oninput = function() {
//   output.innerHTML = this.value;
// }

var content_examples = [
  "colorful alien life forms swirling through outer space",
  "kaleidoscopic view of a future apartment in the year 3000",
  "futuristic art gallery filled with people in the year 3000",
  "crowded medieval town square with merchants",
  "merpeople swimming above the mythical city of atlantis",
  "humanoid robots walking around a convention center"
];

var media_examples = [
  "360 photo",
  "black and white photograph",
  "color photo",
  "watercolor",
  "oil painting",
  "pencil sketch",
  "digital art",
  "3D model"
];

var style_examples = [
  "Picasso",
  "cubism",
  "surrealism",
  "Van Gogh",
  "abstract",
  "Marvel Comics",
  "trippy",
  "sci fi",
  "anime"
];

var content_btn = document.getElementById("content_btn");
var content_ex = document.getElementById("content_ex");
var media_btn = document.getElementById("media_btn");
var media_ex = document.getElementById("media_ex");
var style_btn = document.getElementById("style_btn");
var style_ex = document.getElementById("style_ex");
content_btn.onclick = function() {
  rand_idx = Math.floor(Math.random() * content_examples.length);
  content_ex.innerText = content_examples[rand_idx];
}

// media_btn.onclick = function() {
//   rand_idx = Math.floor(Math.random() * media_examples.length);
//   media_ex.innerText = media_examples[rand_idx];
// }

// style_btn.onclick = function() {
//   rand_idx = Math.floor(Math.random() * style_examples.length);
//   style_ex.innerText = style_examples[rand_idx];
// }

submit_btn.onclick = function() {
    fetch('http://localhost:5000/sd_request')
        .then(function (result) {
            console.log(result);
        })
        .catch(function (err) {
            console.error(err);
        });
}

var rand_seed = document.getElementById("rand_seed");
var same_seed = document.getElementById("same_seed");

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function visibilityToggle() {
  setInterval(function() {
    vis = document.getElementById("underscore").style.visibility;
    if (vis == "hidden") {
      document.getElementById("underscore").style.visibility = "visible";
    } else {
      document.getElementById("underscore").style.visibility = "hidden";
    }
  }, 500);
}

async function get_input() {
  console.log("INPUT LOOP STARTING. COUNTDOWN");
  for (let i = 1; i >= 0; i--) {
    console.log(i);
    await sleep(1000);
  }

  while(true) {
    let prompt_content = document.getElementById("prompt_content").value;
    let prompt_media = document.getElementById("prompt_media").value;
    let prompt_style = document.getElementById("prompt_style").value;

    // Combine prompt strings
    let prompt_str = "";

    // prompt_str = prompt_content + "\n" + prompt_media + "\n" + prompt_style

    if (prompt_content.length > 0 && (prompt_media.length > 0 || prompt_style.length > 0))
      prompt_str += prompt_content + ", ";
    else
      prompt_str += prompt_content;
    if (prompt_media.length > 0 && prompt_style.length > 0)
      prompt_str += prompt_media + ", " + prompt_style
    else if (prompt_media.length > 0)
      prompt_str += prompt_media
    else if (prompt_style.length > 0)
      prompt_str += prompt_style

      // prompt_str = prompt_content + ", " + prompt_media + ", " + prompt_style;

    // Clean prompt string
    prompt_str = prompt_str.replace(/\r?\n|\r/g, ",");
    console.log(prompt_str);
    document.getElementById("last_prompt").innerText = prompt_str;
    document.getElementById("last_seed").innerText = rand_seed.value;

    let interface_data = new FormData();
    interface_data.append("prompt", prompt_str);
    // interface_data.append("cfg_scale", cfg_slider.value);
    interface_data.append("cfg_scale", 7);
    interface_data.append("seed", rand_seed.value)
    const response = await fetch("", {
      method: "POST",
      body: interface_data
    });
    sd_job = await response.json();
    console.log(sd_job);

    if (!same_seed.checked) {
      rand_seed.value = Math.floor(Math.random() * 10000);
    }

    est_time(sd_job);
  
    await sleep(5000);
  }
}


async function est_time(sd_job) {
  let last_runtime = parseInt(sd_job.runtime) + 5;

  if (current_id != sd_job.id && !first_count) {
    console.log("received new job...");
    interrupt = true;
  }

  first_count = false;
  current_id = sd_job.id;

  for (let time_left = last_runtime; time_left >= 0; time_left--) {
    await sleep(1000);
    // console.log(time_left);
    if (interrupt) {
      if (document.getElementById("estimated_runtime").innerText != "0") {
        console.log("got interrupt signal. exiting loop.");
        interrupt = false;
        return;
      } else {
        interrupt = false;
      }
    }
    document.getElementById("estimated_runtime").innerText = time_left;
  }
}

visibilityToggle();
get_input();

// await fetch("", {
//   method: "POST",
//   body: interface_data
//   // body: JSON.stringify({
//   //   prompt: prompt
//   // }),
//   // headers: {
//   //   "Content-type": "application/json; charset=UTF-8"
//   // }
// });