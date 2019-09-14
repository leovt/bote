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
        question = result[key].question;
        document.getElementById('answer').setAttribute('style', '');
        if (question.question == 'ChooseAction'){
          var choices = document.getElementById('choices');
          choices.innerHTML = "";
          for (var action in result[key].question.choices) {
            var opt = document.createElement('input');
            opt.setAttribute('value', action);
            opt.setAttribute('id', 'action-' + action);
            opt.setAttribute('name', 'action');
            opt.setAttribute('type', 'radio');
            if (action==0)
              opt.setAttribute('checked', '');
            choices.appendChild(opt);
            var lbl = document.createElement('label');
            lbl.setAttribute('for', 'action-' + action);
            lbl.appendChild(document.createTextNode(result[key].question.choices[action]));
            choices.appendChild(lbl);
            choices.appendChild(document.createElement('br'));
          }
        }
        else if (question.question == 'DeclareAttackers') {
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
  var answer;
  if (question.question == 'ChooseAction'){
    var radios = document.getElementsByName('action');
    for (var i = 0, length = radios.length; i < length; i++) {
      if (radios[i].checked) {
        answer = +radios[i].value;
        break;
      }
    }
  }
  httpRequest.send(JSON.stringify({"answer": answer}));
  document.getElementById('answer').setAttribute('style', 'display: none;');
}
