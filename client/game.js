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
    result = JSON.parse(httpRequest.responseText);
    var list = document.getElementById('log');
    forEachKeyValue(result, (key, event) => {
      log_count += 1;
      console.log(event.event_id);
      let entry = document.createElement('li');
      entry.appendChild(document.createTextNode(JSON.stringify(event)));
      if (event.event_id == 'DrawCardEvent'){
        if (event.player.is_me) {
          let hand = document.getElementById('hand');
          hand.appendChild(getCardElement(event.card));
        } else {
          let hand = document.getElementById('op-hand');
          hand.appendChild(getBackfaceCardElement(event.card_id));
        }
      }
      if (event.event_id == 'EnterTheBattlefieldEvent' && event.card) {
        let bf;
        if (event.controller.is_me){
          bf = document.getElementById('bf-mine');
        } else {
          bf = document.getElementById('bf-theirs');
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
        let stack = document.getElementById('stack');
        animatedMove(getCardElement(event.card), stack);
      }
      if (event.event_id == 'TapEvent') {
        getCardElement(event.permanent.card).classList.add('tap');
      }
      if (event.event_id == 'UntapEvent') {
        getCardElement(event.permanent.card).classList.remove('tap');
      }
      if (event.event_id == 'AddEnergyEvent' || event.event_id == 'PayEnergyEvent') {
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
    });
    list.scrollTop = list.scrollHeight; //Scroll to bottom of log
  });
  httpRequest.open("GET", `${game_uri}/log?first=${log_count}`);
  httpRequest.send();
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

function forEachKeyValue(object, receiver) {
  for (var key in object) {
    // skip loop if the property is from prototype
    if (!object.hasOwnProperty(key)) continue;
    receiver(key, object[key]);
  }
}

function build_question_ui(event){
  question = event.question;
  document.getElementById('answer').setAttribute('style', '');
  var choices = document.getElementById('choices');
  choices.innerHTML = "";
  if (question.question == 'ChooseAction'){
    var first = true;
    var makeOnclick = function(action_id) {
      return function () {
        document.getElementById(`action-${action_id}`).checked = true;
        send_answer();
      };
    };
    forEachKeyValue(question.choices, (action_id, action) => {
      choices.appendChild(make_input_with_label(
        type = 'radio',
        value = action_id,
        name = 'action',
        label = action.text,
        checked = first
      ));
      first = false;
      choices.appendChild(document.createElement('br'));
      if (action.action == 'play') {
        let card = document.getElementById(action.card_id);
        card.classList.add('playable');
        card.onclick = makeOnclick(action_id);
      }
      if (action.action == 'activate') {
        let card = document.getElementById(action.card_id);
        card.classList.add('activateable');
        let menu = document.getElementById('menu-'+action.card_id);
        if (!menu) {
          menu = document.createElement('div');
          menu.setAttribute('id', 'menu-'+action.card_id);
          menu.setAttribute('class', 'menu');
          menu.setAttribute('style', 'display: none;');
          document.body.appendChild(menu);
        }
        let button = document.createElement('button');
        button.appendChild(document.createTextNode(action.text));
        button.onclick = makeOnclick(action_id);
        menu.appendChild(button);
        card.onmouseenter = function (event) {
          let menu = document.getElementById('menu-'+this.id);
          let rect = this.getBoundingClientRect();
          menu.setAttribute('style', `left:${rect.right}px; top:${rect.top}px`);
        };
      }
    });
  }
  else if (question.question == 'DeclareAttackers') {
    forEachKeyValue(question.choices, (action_id, action) => {
      choices.appendChild(make_input_with_label(
        type = 'checkbox',
        value = action_id,
        name = 'attacker',
        label = action,
        checked = false
      ));
      choices.appendChild(document.createElement('br'));
    });
  }
  else if (question.question == 'DeclareBlockers') {
    forEachKeyValue(question.choices, (action_id, action) => {
      choices.appendChild(document.createTextNode(action.candidate));
      choices.appendChild(make_input_with_label(
        type = 'radio',
        value = 'noblock',
        name = 'cand-' + action_id,
        label = 'Do not block',
        checked = true
      ));
      choices.appendChild(document.createTextNode(' or block one of: '));
      forEachKeyValue(action.attackers, (attacker_id, attacker) => {
        choices.appendChild(make_input_with_label(
          type = 'radio',
          value = attacker_id,
          name = 'cand-' + action_id,
          label = attacker,
          checked = false
        ));
      });
      choices.appendChild(document.createElement('br'));
    });
  }
  else if (question.question == 'OrderBlockers') {
    choices.innerHTML = "";
    forEachKeyValue(question.choices, (action_id, action) => {
      choices.appendChild(document.createTextNode(action.attacker));
      var list = document.createElement('ol');
      list.setAttribute('id', action_id);
      choices.appendChild(list);
      for (var blocker in action.blockers){
        list.appendChild(make_reorderable_listitem(
          value = blocker,
          label = action.blockers[blocker]
        ));
      }
    });
  }
  else {
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
    for (let i = 0, length = radios.length; i < length; i++) {
      if (radios[i].checked) {
        answer = radios[i].value;
        break;
      }
    }
    forEachKeyValue(question.choices, (action_id, action) => {
      if (action.action == 'play') {
        let card = document.getElementById(action.card_id);
        card.classList.remove('playable');
        card.removeAttribute('onclick');
      }
      if (action.action == 'activate') {
        let card = document.getElementById(action.card_id);
        card.classList.remove('activateable');
        let menu = document.getElementById('menu-'+action.card_id);
        if (menu) menu.parentNode.removeChild(menu);
      }
    });
  }
  if (question.question == 'DeclareAttackers'){
    answer = [];
    var attackers = document.getElementsByName('attacker');
    for (let i = 0, length = attackers.length; i < length; i++) {
      if (attackers[i].checked) {
        answer.push(attackers[i].value);
      }
    }
  }
  if (question.question == 'DeclareBlockers'){
    answer = {};
    forEachKeyValue(question.choices, (action_id, action) => {
      var attackers = document.getElementsByName('cand-' + action_id);
      for (var i = 0, length = attackers.length; i < length; i++) {
        if (attackers[i].checked) {
          if (attackers[i].value != 'noblock')
            answer[action_id] = attackers[i].value;
          break;
        }
      }
    });
  }
  if (question.question == 'OrderBlockers'){
    let choices = document.getElementById('choices');
    answer = {};
    let attackers = choices.getElementsByTagName('ol');
    for (let i = 0, length = attackers.length; i < length; i++) {
      var ans = [];
      var blockers = attackers[i].getElementsByTagName('li');
      for (let j = 0; j < blockers.length; j++) {
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
