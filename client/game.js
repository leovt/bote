function getCardElement(card){
  var element = document.getElementById(card.card_id);
  if (!element) {
    element = document.createElement('img');
    element.setAttribute('id', card.card_id);
    element.setAttribute('class', 'card');
  }
  element.setAttribute('src', card.url);
  return element;
}

function getBackfaceCardElement(card_id){
  var element = document.getElementById(card_id);
  if (!element) {
    element = document.createElement('img');
    element.setAttribute('id', card_id);
    element.setAttribute('class', 'card');
    element.setAttribute('src', 'backface.png');
  }
  return element;
}

function log_refresh () {
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    result = JSON.parse(httpRequest.responseText)
    var list = document.getElementById('log');
    for (var key in result) {
      let event = result[key];
      log_count += 1;
      console.log(event.event_id)
      var entry = document.createElement('li');
      entry.appendChild(document.createTextNode(JSON.stringify(event)));
      if (event.event_id == 'DrawCardEvent'){
        if (event.player.is_me) {
          var hand = document.getElementById('hand');
          hand.appendChild(getCardElement(event.card));
        } else {
          var hand = document.getElementById('op-hand');
          hand.appendChild(getBackfaceCardElement(event.card_id));
        }
      }
      if (event.event_id == 'EnterTheBattlefieldEvent' && event.card) {
        var bf;
        if (event.controller.is_me){
          var bf = document.getElementById('bf-mine');
        } else {
          var bf = document.getElementById('bf-theirs');
        }
        animatedMove(getCardElement(event.card), bf);
      }
      if (event.event_id == 'PutInGraveyardEvent') {
        let target;
        if (event.card.owner.is_me){
          target = document.getElementById('my-graveyard');
        } else {
          target = document.getElementById('op-graveyard');
        }
        animatedMove(getCardElement(event.card), target);
      }
      if (event.event_id == 'CastSpellEvent' && event.card) {
        var stack = document.getElementById('stack');
        animatedMove(getCardElement(event.card), stack);
      }
      if (event.event_id == 'TapEvent') {
        getCardElement(event.permanent.card).classList.add('tap');
      }
      if (event.event_id == 'UntapEvent') {
        getCardElement(event.permanent.card).classList.remove('tap');
      }
      if (event.event_id == 'AddEnergyEvent'
          || event.event_id == 'PayEnergyEvent') {
        document.getElementById(event.player.is_me ? 'my-energy' : 'op-energy')
                .innerText = `Energy: ${event.new_total}`;
      }
      if (event.event_id == 'ClearPoolEvent') {
        document.getElementById(event.player.is_me ? 'my-energy' : 'op-energy')
                .innerText = "Energy: {0}";
      }
      if (event.event_id == 'PlayerDamageEvent') {
        document.getElementById(event.player.is_me ? 'my-life' : 'op-life')
                .innerText = `Life: ${event.new_total}`;
      }
      if (event.event_id == 'StepEvent') {
        indicate_step(event);
        if (event.step == 'BEGIN_COMBAT') {
          let combat = document.getElementById('combat');
          combat.innerHTML = '';
          if (event.active_player.is_me) {
            combat.classList.remove('opponent-attacking');
          } else {
            combat.classList.add('opponent-attacking');
          }
        }
      }
      if (event.event_id == 'QuestionEvent' && event.question.player.is_me) {
        build_question_ui(event);
      }
      if (event.event_id == 'AttackEvent') {
        let attacker = getCardElement(event.attacker.card);
        let fightbox = document.createElement('div');
        fightbox.setAttribute('id', `fbx-${attacker.id}`);
        fightbox.setAttribute('class', 'fightbox');
        let blockers = document.createElement('div');
        blockers.setAttribute('id', `blk-${attacker.id}`);
        blockers.setAttribute('class', 'blockers');
        fightbox.appendChild(blockers);
        document.getElementById('combat').appendChild(fightbox);
        animatedMove(attacker, fightbox);
      }
      if (event.event_id == 'BlockEvent') {
        let attacker = getCardElement(event.attacker.card);
        let blockers = document.getElementById(`blk-${attacker.id}`);
        for (let i = 0; i<event.blockers.length; i++) {
          let blocker = getCardElement(event.blockers[i].card);
          animatedMove(blocker, blockers);
        }
      }
      if (event.event_id == 'RemoveFromCombatEvent') {
        let card = getCardElement(event.permanent.card);
        let bf;
        if (event.permanent.controller.is_me){
          bf = document.getElementById('bf-mine');
        } else {
          bf = document.getElementById('bf-theirs');
        }
        animatedMove(card, bf);
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

function animatedMove(element, target, delay=900){
  if (target === element.parentNode){
    return;
  }
  var oldClientRect = element.getBoundingClientRect();
  target.appendChild(element);
  var newClientRect = element.getBoundingClientRect();

  document.body.appendChild(element);

  element.setAttribute('style',
   `position: absolute;
    left: ${oldClientRect.left}px; top: ${oldClientRect.top}px;
    z-index:1000;
    margin:0px;`);

  element.classList.add('inmotion');

  function finalizer(){
    target.appendChild(element);
    element.removeAttribute('style');
    element.classList.remove('inmotion');
  }

  if (element.animate) {
    element.animate([
    // keyframes
    { left: `${oldClientRect.left}px`, top: `${oldClientRect.top}px` },
    { left: `${newClientRect.left}px`, top: `${newClientRect.top}px` }
    ], {
    // timing options
    duration: delay,
    iterations: 1,
    easing: "ease-in-out"
    });
    window.setTimeout(finalizer, delay);
  }
  else {
    /* animation not available, immediately finalize */
    finalizer();
  }
}
