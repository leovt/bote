function log_refresh () {
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    result = JSON.parse(httpRequest.responseText)
    var list = document.getElementById('log');
    for (var key in result) {
      log_count += 1;
      console.log(result[key].event_id)
      var entry = document.createElement('li');
      entry.appendChild(document.createTextNode(JSON.stringify(result[key])));
      if (result[key].event_id == 'DrawCardEvent' && result[key].card) {
        var img = document.createElement('img');
        img.setAttribute('src', result[key].card.url);
        img.setAttribute('style', 'height:5em;');
        entry.appendChild(img);
      }
      if (result[key].event_id == 'QuestionEvent') {
        var menu = document.getElementById('question');
        question.innerHTML = "";
        for (var action in result[key].question.choices) {
          var opt = document.createElement('option');
          opt.setAttribute('value', action);
          opt.appendChild(document.createTextNode(result[key].question.choices[action]));
          question.appendChild(opt);
        }
      }
      list.appendChild(entry);
    }
    list.scrollTop = list.scrollHeight; //Scroll to bottom of log
  })
  httpRequest.open("GET", `${game_uri}/log?first=${log_count}`);
  httpRequest.send()
}


function send_answer () {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `${game_uri}/answer`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.addEventListener("load", log_refresh);
  var answer = +document.getElementById('question').value;
  httpRequest.send(JSON.stringify({"answer": answer}));
}
