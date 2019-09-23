function getCardElement(card){
  var element = document.getElementById(card.card_id);
  if (!element) {
    element = document.createElement('img');
    element.setAttribute('id', card.card_id);
    element.setAttribute('class', 'card');
    element.setAttribute('src', card.url);
    element.setAttribute('style', 'height:5em;');
  }
  return element;
}

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
        var hand = document.getElementById('hand');
        hand.appendChild(getCardElement(result[key].card));
      }
      if (result[key].event_id == 'EnterTheBattlefieldEvent' && result[key].card) {
        var bf;
        if (result[key].controller.is_me){
          var bf = document.getElementById('bf-mine');
        } else {
          var bf = document.getElementById('bf-theirs');
        }
        bf.appendChild(getCardElement(result[key].card));
      }
      if (result[key].event_id == 'CastSpellEvent' && result[key].card) {
        var stack = document.getElementById('stack');
        stack.appendChild(getCardElement(result[key].card));
      }
      if (result[key].event_id == 'TapEvent') {
        getCardElement(result[key].permanent.card).classList.add('tap');
      }
      if (result[key].event_id == 'UntapEvent') {
        getCardElement(result[key].permanent.card).classList.remove('tap');
      }
      if (result[key].event_id == 'StepEvent') {
        indicate_step(result[key]);
      }
      if (result[key].event_id == 'QuestionEvent' && result[key].question.choices) {
        build_question_ui(result[key]);
      }
      list.appendChild(entry);
    }
    list.scrollTop = list.scrollHeight; //Scroll to bottom of log
  })
  httpRequest.open("GET", `${game_uri}/log?first=${log_count}`);
  httpRequest.send()
}

function make_input_with_label(type, value, name, label, checked){
  var span = document.createElement('span');
  var input = document.createElement('input');
  var input_id = `${name}-${value}`;
  input.setAttribute('value', value);
  input.setAttribute('id', input_id);
  input.setAttribute('name', name);
  input.setAttribute('type', type);
  if (checked)
    input.setAttribute('checked', '');
  span.appendChild(input);

  var lbl = document.createElement('label');
  lbl.setAttribute('for', input_id);
  lbl.appendChild(document.createTextNode(label));
  span.appendChild(lbl);
  return span;
}

function make_reorderable_listitem(value, label) {
  var li = document.createElement('li');
  li.setAttribute('id', value);

  var btn_down = document.createElement('button');
  btn_down.setAttribute('onclick', `reorderDown('${value}')`);
  btn_down.appendChild(document.createTextNode('▼'));

  var btn_up = document.createElement('button');
  btn_up.setAttribute('onclick', `reorderUp('${value}')`);
  btn_up.appendChild(document.createTextNode('▲'));

  li.appendChild(btn_down);
  li.appendChild(document.createTextNode(label));
  li.appendChild(btn_up);
  return li;
}

function build_question_ui(event){
  question = event.question;
  document.getElementById('answer').setAttribute('style', '');
  var choices = document.getElementById('choices');
  choices.innerHTML = "";
  if (question.question == 'ChooseAction'){
    var first = true;
    for (var action in question.choices) {
      choices.appendChild(make_input_with_label(
        type = 'radio',
        value = action,
        name = 'action',
        label = question.choices[action],
        checked = first
      ));
      first = false;
      choices.appendChild(document.createElement('br'));
    }
  }
  else if (question.question == 'DeclareAttackers') {
    choices.innerHTML = "";
    for (var action in question.choices) {
      choices.appendChild(make_input_with_label(
        type = 'checkbox',
        value = action,
        name = 'attacker',
        label = question.choices[action],
        checked = false
      ));
      choices.appendChild(document.createElement('br'));
    }
  }
  else if (question.question == 'DeclareBlockers') {
    choices.innerHTML = "";
    for (var action in question.choices) {
      choices.appendChild(document.createTextNode(question.choices[action].candidate));
      choices.appendChild(make_input_with_label(
        type = 'radio',
        value = 'noblock',
        name = 'cand-' + action,
        label = 'Do not block',
        checked = true
      ));
      choices.appendChild(document.createTextNode(' or block one of: '));
      for (var attacker in question.choices[action].attackers){
        choices.appendChild(make_input_with_label(
          type = 'radio',
          value = attacker,
          name = 'cand-' + action,
          label = question.choices[action].attackers[attacker],
          checked = false
        ));
      }
      choices.appendChild(document.createElement('br'));
    }
  }
  else if (question.question == 'OrderBlockers') {
    choices.innerHTML = "";
    for (var action in question.choices) {
      choices.appendChild(document.createTextNode(question.choices[action].attacker));
      var list = document.createElement('ol');
      list.setAttribute('id', action);
      choices.appendChild(list);
      for (var blocker in question.choices[action].blockers){
        list.appendChild(make_reorderable_listitem(
          value = blocker,
          label = question.choices[action].blockers[blocker]
        ));
      }
    }
  }
  else {
    choices.innerHTML = "";
    choices.appendChild(document.createTextNode(JSON.stringify(question)));
  }
}

function send_answer () {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `${game_uri}/answer`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.addEventListener("load", function(){
    document.getElementById('answer').setAttribute('style', 'display: none;');
    log_refresh();
  });
  var answer;
  if (question.question == 'ChooseAction'){
    var radios = document.getElementsByName('action');
    for (var i = 0, length = radios.length; i < length; i++) {
      if (radios[i].checked) {
        answer = radios[i].value;
        break;
      }
    }
  }
  if (question.question == 'DeclareAttackers'){
    answer = [];
    var attackers = document.getElementsByName('attacker');
    for (var i = 0, length = attackers.length; i < length; i++) {
      if (attackers[i].checked) {
        answer.push(attackers[i].value);
      }
    }
  }
  if (question.question == 'DeclareBlockers'){
    answer = {};
    for (var action in question.choices) {
      var attackers = document.getElementsByName('cand-' + action);
      for (var i = 0, length = attackers.length; i < length; i++) {
        if (attackers[i].checked) {
          if (attackers[i].value != 'noblock')
            answer[action] = attackers[i].value;
          break;
        }
      }
    }
  }
  if (question.question == 'OrderBlockers'){
    var choices = document.getElementById('choices');
    answer = {};
    var attackers = choices.getElementsByTagName('ol');
    for (var i = 0, length = attackers.length; i < length; i++) {
      var ans = [];
      var blockers = attackers[i].getElementsByTagName('li');
      for (var j = 0; j < blockers.length; j++) {
        ans.push(blockers[j].id);
      }
      answer[attackers[i].id] = ans;
    }
  }
  httpRequest.send(JSON.stringify({"answer": answer}));
}

function reorderUp(item_id) {
  var item = document.getElementById(item_id);
  var prev = item.previousElementSibling;
  if (prev) {
    item.parentNode.insertBefore(item, prev);
  }
}

function reorderDown(item_id) {
  var item = document.getElementById(item_id);
  var after = item.nextElementSibling;
  if (after) {
    after.parentNode.insertBefore(after, item);
  }
}

var indicate_step = (function() {
  var indicator_position = 36000;
  const STEPS = [
          "UNTAP", "UPKEEP", "DRAW",
          "PRECOMBAT_MAIN",
          "BEGIN_COMBAT", "DECLARE_ATTACKERS", "DECLARE_BLOCKERS",
          "FIRST_STRIKE_DAMAGE", "SECOND_STRIKE_DAMAGE", "END_OF_COMBAT",
          "POSTCOMBAT_MAIN",
          "END", "CLEANUP"];
  return function (event){
    var new_position = 172.5 - 15*STEPS.indexOf(event.step);
    if (!event.active_player.is_me) {
      new_position += 180;
    }
    while (new_position > indicator_position) {
      new_position -= 360;
    }
    indicator_position = new_position;

    var svgItem = document.getElementById("stepindicator")
                          .contentDocument
                          .getElementById("indicator");
    svgItem.setAttribute("style", `transform: rotate(${indicator_position}deg);`);
  };
})();
