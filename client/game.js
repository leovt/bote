function _getCardElement(card_id, url){
  var element = document.getElementById(card_id);
  if (!element) {
    element = document.createElement('div');
    var img = document.createElement('img');
    img.onmouseover = function() {
      var cardview = document.getElementById('cardview');
      cardview.src = img.src;
      cardview.style.visibility = "visible";
    };
    img.onmouseout = function() {
      var cardview = document.getElementById('cardview');
      cardview.style.visibility = "hidden";
    };

    element.setAttribute('id', card_id);
    element.setAttribute('class', 'card');
    element.appendChild(img);
  }
  element.firstChild.setAttribute('src', url);
  return element;
}

function getBackfaceCardElement(card_id){
  return _getCardElement(card_id, BACKFACE_URL);
}

function getCardElement(card){
  return _getCardElement(card.card_id, card.url);
}

function write_message(message) {
  let messages = document.getElementById('messages');
  let entry = document.createElement('li');
  entry.appendChild(document.createTextNode(message));
  messages.appendChild(entry);
  messages.scrollTop = messages.scrollHeight;
}

nextEvent = 0;
function handleGameEvent(event) {
  //console.log({nextEvent: nextEvent, event_no: event.event_no, event_id: event.event_id});
  console.assert(event.event_no >= nextEvent);
  nextEvent = event.event_no + 1;
  let handler = gameEventHandler[event.event_id];
  if (handler) {
    handler(event);
  }
}

const gameEventHandler = {
  DrawCardEvent: function(event) {
    if (event.player.is_me) {
      let hand = document.getElementById('hand');
      hand.appendChild(getCardElement(event.card));
      write_message(`You draw ${event.card.name}.`);
    } else {
      let hand = document.getElementById('op-hand');
      hand.appendChild(getBackfaceCardElement(event.card_id));
      write_message(`${event.player.name} draws a card.`);
    }
  },

  EnterTheBattlefieldEvent: function(event) {
    let tgt = document.getElementById(event.controller.is_me ? 'bf-mine' : 'bf-theirs');
    animatedMove(getCardElement(event.card), tgt);
    write_message(`${event.card.name} enters the battlefield.`);
  },

  PutInGraveyardEvent: function(event) {
    write_message(`${event.card.name} went to the graveyard.`);
    let tgt = document.getElementById(event.card.owner.is_me ? 'my-graveyard' : 'op-graveyard');
    animatedMove(getCardElement(event.card), tgt);
  },

  DiscardEvent: function(event) {
    write_message(` discarded ${event.card.name}.`);
    let tgt = document.getElementById(event.card.owner.is_me ? 'my-graveyard' : 'op-graveyard');
    animatedMove(getCardElement(event.card), tgt);
  },

  CastSpellEvent: function(event) {
    if (event.card) {
      let tgt = document.getElementById('stack');
      animatedMove(getCardElement(event.card), tgt);
    }
  },

  ActivateAbilityEvent: function(event) {
    let stack = document.getElementById('stack');
    let card = getCardElement(event.permanent.card);
    let rect = card.getBoundingClientRect();
    let item = document.createElement('div');
    item.innerText = "Effect of " + event.permanent.card.name;
    item.className = "card ability";
    item.id = event.stack_id;
    stack.appendChild(item);
  },

  ResolveEvent: function(event) {
    let stack = document.getElementById('stack');
    let stack_id = event.tos.stack_id;
    if (event.tos.ability) {
      stack.removeChild(document.getElementById(stack_id));
    }
  },

  TapEvent: function(event) {
    getCardElement(event.permanent.card).classList.add('tap');
  },

  UntapEvent: function(event) {
    getCardElement(event.permanent.card).classList.remove('tap');
  },

  AddEnergyEvent: function(event) {
    document.getElementById(event.player.is_me ? 'my-energy' : 'op-energy')
            .innerText = `Energy: ${event.new_total}`;
  },

  PayEnergyEvent: function(event) {
    document.getElementById(event.player.is_me ? 'my-energy' : 'op-energy')
            .innerText = `Energy: ${event.new_total}`;
  },

  ClearPoolEvent: function(event) {
    document.getElementById(event.player.is_me ? 'my-energy' : 'op-energy')
            .innerText = "Energy: {0}";
  },

  PlayerDamageEvent: function(event) {
    write_message(`${event.player.name} received ${event.damage} damage.`);
    document.getElementById(event.player.is_me ? 'my-life' : 'op-life')
            .innerText = `Life: ${event.new_total}`;
  },

  StepEvent: function(event) {
    indicate_step(event);
    if (event.step == 'BEGIN_COMBAT') {
      let combat = document.getElementById('combat');
      combat.innerHTML = '';
      if (event.active_player.is_me) {
        combat.classList.remove('opponent-attacking');
      } else {
        combat.classList.add('opponent-attacking');
      }
      attackers = {};
    }
    if (event.step == 'POSTCOMBAT_MAIN') {
      forEachKeyValue(attackers, (key, attacker) => attacker.destroy());
      attackers = null;
    }
  },

  AttackEvent: function(event) {
    write_message(`${event.player.name} received ${event.damage} damage.`);
    let attacker = attackers[event.attacker.card.card_id];
    if (!attacker) {
      attacker = Attacker(event.attacker.card.card_id, null);
      attackers[event.attacker.card.card_id] = attacker;
    }
    attacker.attack();
    attacker.stopInteracting();
  },

  BlockEvent: function(event) {
    let attacker = attackers[event.attacker.card.card_id];
    event.blockers.forEach(blocker => {
      let card = getCardElement(blocker.card);
      animatedMove(card, attacker.blockerDiv);
    });
  },

  RemoveFromCombatEvent: function(event) {
    if (attackers) {
      let attacker = attackers[event.permanent.card.card_id];
      if (attacker) {
        attacker.retreat();
      }
      else {
        let card = getCardElement(event.permanent.card);
        if (event.permanent.controller.is_me)
          animatedMove(card, document.getElementById('bf-mine'));
        else
          animatedMove(card, document.getElementById('bf-theirs'));
      }
    }
  },
};


function pass_only_choice(question) {
  if (question.question == 'ChooseAction') {
    var pass;
    var count = 0;
    forEachKeyValue(question.choices, (action_id, action) => {
      if (action.action === 'pass') {
        pass = action_id;
      }
      count += 1;
    });
    if (count == 1) {
      return pass;
    }
  }
}

log_refresh_running = false;
function log_refresh () {
  if (log_refresh_running) {
    return;
  }
  log_refresh_running = true;
  window.clearTimeout(window.log_refresh_timeout_id);
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    result = JSON.parse(httpRequest.responseText);
    result.event_log.forEach(handleGameEvent);
    if (result.question) {
      var btn = document.getElementById('confirm');
      btn.innerText = "...";
      btn.disabled = true;
      if (result.question.player.is_me) {
        var pass_oc = pass_only_choice(result.question);
        var autopass = document.getElementById('autopass');
        if (autopass.checked && pass_oc) {
          window.setTimeout(send_answer, 1000, pass_oc);
        }
        else {
          build_question_ui(result.question);
        }
      }
      else {
        btn.innerText = "waiting for " + result.question.player.name;
        window.log_refresh_timeout_id = window.setTimeout(log_refresh, 1000);
      }
    }
    log_refresh_running = false;
  });
  let filter = Object.getOwnPropertyNames(gameEventHandler).join("_");
  httpRequest.open("GET", `${game_uri}/log?first=${nextEvent}&filter=${filter}`);
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


function Attacker(card_id, choice_id) {
  var cardElement = document.getElementById(card_id);
  cardElement.classList.remove('inmotion');
  cardElement.classList.remove('placeholder');
  cardElement.setAttribute('style', '');

  var cloneElement = cardElement.cloneNode(true);
  var placeholderElement = cardElement.cloneNode(true);
  var checkboxElement = document.getElementById(`attacker-${choice_id}`);
  var isAttacking = false;


  cloneElement.classList.add('inmotion');
  cloneElement.classList.add('clone');
  cloneElement.id += "_c";
  cardElement.classList.add('placeholder');
  placeholderElement.classList.add('placeholder');
  placeholderElement.id += "_p";

  var fightbox = document.createElement('div');
  fightbox.setAttribute('class', 'fightbox');

  var blockerDiv = document.createElement('div');
  blockerDiv.setAttribute('class', 'blockers');
  fightbox.appendChild(blockerDiv);

  fightbox.appendChild(placeholderElement);
  document.getElementById('combat').appendChild(fightbox);
  document.body.appendChild(cloneElement);

  function destroy() {
    cardElement.classList.remove('placeholder');
    cloneElement.remove();
    placeholderElement.remove();
    fightbox.remove();
  }

  function stopInteracting() {
    cloneElement.setAttribute('style', 'display: none;');
    if (isAttacking) {
      placeholderElement.classList.remove('placeholder');
    }
    else {
      cardElement.classList.remove('placeholder');
    }
  }

  function attack() {
    let rect = placeholderElement.getBoundingClientRect();
    cloneElement.setAttribute('style',
      `left:${rect.left + window.scrollX}px; top:${rect.top + window.scrollY}px`);
    isAttacking = true;
    if (checkboxElement)
      checkboxElement.checked = true;

    let btn = document.getElementById('confirm');
    btn.innerText = "Attack";
  }

  function retreat() {
    let rect = cardElement.getBoundingClientRect();
    cloneElement.setAttribute('style',
      `left:${rect.left + window.scrollX}px; top:${rect.top + window.scrollY}px`);
    isAttacking = false;
    if (checkboxElement)
      checkboxElement.checked = false;
    let btn = document.getElementById('confirm');
    btn.innerText = "Skip Attack";
    forEachKeyValue(attackers, (_, att) => {if (att.isAttacking()) btn.innerText = "Attack";});
  }

  function toggle() {
    if (isAttacking)
      retreat();
    else
      attack();
  }

  function addBlocker(blocker, choice_id) {
    var cardElement = document.getElementById(blocker.card_id);
    cardElement.classList.remove('inmotion');
    cardElement.classList.add('placeholder');
    cardElement.setAttribute('style', '');
    var placeholderElement = cardElement.cloneNode(true);
    placeholderElement.classList.add('selectable');

    placeholderElement.id += "_blocking_" + card_id;

    blockerDiv.appendChild(placeholderElement);

    blocker.placeholders.push(placeholderElement);

    function click() {
      blocker.placeholders.forEach(element => element.classList.add('placeholder'));
      if (blocker.blocking === choice_id) {
        blocker.blocking = "noblock";
        cardElement.classList.remove('placeholder');
      }
      else {
        blocker.blocking = choice_id;
        cardElement.classList.add('placeholder');
        placeholderElement.classList.remove('placeholder');
      }
    }

    placeholderElement.addEventListener('click', click);
  }


  cloneElement.onclick = toggle;
  cloneElement.classList.add('selectable');

  retreat();

  return {
    'attack': attack,
    'retreat': retreat,
    'isAttacking': () => isAttacking,
    'toggle': toggle,
    'stopInteracting': stopInteracting,
    'destroy': destroy,
    'fightbox': fightbox,
    'blockerDiv': blockerDiv,
    'choice_id': choice_id,
    'addBlocker': addBlocker
  };
}


function build_question_ui(question){
  if (window.question && window.question.id === question.id) {
    // this question is already setup
    return;
  }
  cleanupChooseActionUI();
  window.question = question;
  document.getElementById('answer').setAttribute('style', '');
  var choices = document.getElementById('choices');
  choices.innerHTML = "";
  if (question.question == 'ChooseAction'){
    var first = true;
    var makeOnclick = function(action_id) {
      return function () {
        send_answer(action_id);
      };
    };
    var btn = document.getElementById('confirm');
    btn.innerText = question.question;
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
      if (action.action == "pass") {
        make_ans_button(action.text, makeOnclick(action_id));
      }
      if (action.action == 'play') {
        let card = document.getElementById(action.card_id);
        card.classList.add('playable');
        card.onclick = makeOnclick(action_id);
      }
      if (action.action == 'discard') {
        let card = document.getElementById(action.card_id);
        card.classList.add('discardable');
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
          card.appendChild(menu);
        }
        let button = document.createElement('button');
        button.appendChild(document.createTextNode(action.text));
        button.onclick = makeOnclick(action_id);
        menu.appendChild(button);
        card.onmouseenter = function (event) {
          let menu = document.getElementById('menu-'+this.id);
          if (!menu)
            return;
          let rect = this.getBoundingClientRect();
          menu.setAttribute('style', '');
        };
        card.onmouseleave = function (event) {
          let menu = document.getElementById('menu-'+this.id);
          if (!menu)
            return;
          let rect = this.getBoundingClientRect();
          menu.setAttribute('style', 'display: none;');
        };
        if (menu.childElementCount == 1) {
          card.onclick = makeOnclick(action_id);
        }
      }
    });
  }
  else if (question.question == 'DeclareAttackers') {
    write_message("Declare your attackers and confirm by clicking on the turn indicator.");
    make_ans_button("Skip Attack", get_and_send_answer);
    forEachKeyValue(question.choices, (action_id, action) => {
      choices.appendChild(make_input_with_label(
        type = 'checkbox',
        value = action_id,
        name = 'attacker',
        label = action.name,
        checked = false
      ));
      choices.appendChild(document.createElement('br'));

      let checkbox = document.getElementById(`attacker-${action_id}`);
      let attacker = Attacker(action.card_id, action_id);
      attackers[action.card_id] = attacker;

      checkbox.onchange = function(att, cbx) {
        return function () {
          if (cbx.checked)
            attacker.attack();
          else
            attacker.retreat();
        };
      }(attacker, checkbox);
    });
  }
  else if (question.question == 'DeclareBlockers') {
    write_message("Declare your blockers and confirm by clicking on the turn indicator.");
    make_ans_button("Confirm Blockers", get_and_send_answer);
    forEachKeyValue(question.choices, (action_id, action) => {
      blockers = {};
      forEachKeyValue(action.attackers, (attacker_id, attacker) => {
        blocker = {placeholders: [], blocking: 'noblock', card_id: action.candidate.card.card_id};
        attackers[attacker.card.card_id].addBlocker(blocker, attacker_id);
        blockers[action_id] = blocker;
      });
    });
  }
  else if (question.question == 'OrderBlockers') {
    make_ans_button("Confirm Blocker Order", get_and_send_answer);
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


function cleanupChooseActionUI() {
  if (!window.question) {
    return;
  }
  let btn = document.getElementById('confirm');
  btn.disabled = true;
  btn.removeAttribute('onclick');
  let ind = document.getElementById('stepconfirm');
  ind.removeAttribute('onclick');

  forEachKeyValue(question.choices, (action_id, action) => {
    if (action.action == 'play') {
      let card = document.getElementById(action.card_id);
      card.classList.remove('playable');
      card.removeAttribute('onclick');
    }
    if (action.action == 'discard') {
      let card = document.getElementById(action.card_id);
      card.classList.remove('discardable');
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


function cleanupDeclareAttackersUI(){
}


function cleanupDeclareBlockersUI(){
}


function cleanupOrderBlockersUI(){
}


cleanupFunctions = {
  'ChooseAction': cleanupChooseActionUI,
  'DeclareAttackers': cleanupDeclareAttackersUI,
  'DeclareBlockers': cleanupDeclareBlockersUI,
  'OrderBlockers': cleanupOrderBlockersUI
};

function get_answer() {
  var answer;
  if (question.question == 'ChooseAction'){
    let radios = document.getElementsByName('action');
    answer = Array.from(radios).find(r => r.checked).value;
  }
  if (question.question == 'DeclareAttackers'){
    answer = [];
    forEachKeyValue(attackers, (key, attacker) => {
      if (attacker.isAttacking()) {
        attacker.stopInteracting();
        answer.push(attacker.choice_id);
      }
      else {
        attacker.destroy();
      }
    });
  }
  if (question.question == 'DeclareBlockers'){
    answer = {};
    forEachKeyValue(question.choices, (action_id, action) => {
      let value = blockers[action_id].blocking;
      if (value != 'noblock') answer[action_id] = value;
    });
  }
  if (question.question == 'OrderBlockers'){
    let choices = document.getElementById('choices');
    answer = {};
    let attackers = choices.getElementsByTagName('ol');
    attackers.forEach(attacker => {
      let blockers = attacker.getElementsByTagName('li');
      let ans = Array.from(blockers).map(x => x.id);
      answer[attacker.id] = ans;
    });
  }
  cleanupFunctions[question.question]();
  return answer;
}


function send_answer (answer) {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `${game_uri}/answer`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.addEventListener("load", function(){
    document.getElementById('answer').setAttribute('style', 'display: none;');
    log_refresh();
  });

  httpRequest.send(JSON.stringify({"answer": answer}));
}


function get_and_send_answer () {
  send_answer(get_answer());
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
  const STEPS = {
          "UNTAP":0, "UPKEEP":1, "DRAW":2,
          "PRECOMBAT_MAIN":3,
          "BEGIN_COMBAT":4, "DECLARE_ATTACKERS":5, "DECLARE_BLOCKERS":6,
          "FIRST_STRIKE_DAMAGE":7, "SECOND_STRIKE_DAMAGE":8, "END_OF_COMBAT":9,
          "POSTCOMBAT_MAIN":10,
          "END":11, "CLEANUP":11}; //no cleanup step indicator: stay on "END" position
  return function (event){
    var new_position = 172.5 - 15*STEPS[event.step];
    if (!event.active_player.is_me) {
      new_position += 180;
    }
    while (new_position > indicator_position) {
      new_position -= 360;
    }
    indicator_position = new_position;

    var svgItem = document.getElementById("indicator");
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


function make_ans_button(label, onclick){
  let btn = document.getElementById('confirm');
  let div = document.getElementById('stepconfirm');
  btn.disabled = false;
  btn.innerText = label;
  div.onclick = onclick;
}

function savegame() {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `${game_uri}/save`);
  httpRequest.send();
}
