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

    var modifiers = document.createElement('div');
    modifiers.setAttribute('class', 'modifiers');
    element.appendChild(modifiers);
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

function startVideo() {
  let iframe = document.getElementById('videoconf');
  iframe.src = VIDEOCONFERENCE_URL;
  iframe.style.visibility = 'visible';
}

function write_message(message) {
  let messages = document.getElementById('messages');
  let entry = document.createElement('li');
  entry.appendChild(document.createTextNode(message));
  messages.appendChild(entry);
  messages.scrollTop = messages.scrollHeight;
}

function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function playerBySeat(snapshot, isMe) {
  return snapshot.players.find(player => player.is_me === isMe);
}

function cardElementFromSnapshot(card) {
  if (card.hidden) {
    return getBackfaceCardElement(card.card_id || 'hidden-card');
  }
  return getCardElement(card);
}

function setCardState(element, card, permanent) {
  element.classList.remove('tap', 'damaged', 'attacking', 'blocking');
  if (permanent && permanent.status.tapped) {
    element.classList.add('tap');
  }
  if (permanent && permanent.damage > 0) {
    element.classList.add('damaged');
  }
  if (permanent && permanent.status.attacking_player_id) {
    element.classList.add('attacking');
  }
  if (permanent && permanent.status.blocking_perm_id) {
    element.classList.add('blocking');
  }
  if (permanent && permanent.keywords) {
    permanent.keywords.forEach(keyword => element.classList.add(keyword));
  }
}

function renderZone(elementId, cards) {
  let zone = document.getElementById(elementId);
  clearElement(zone);
  cards.forEach(card => zone.appendChild(cardElementFromSnapshot(card)));
}

const ENERGY_COLOR_MAP = [
  ['red',       '#dd3333'],
  ['yellow',    '#ffcc00'],
  ['blue',      '#3355dd'],
  ['green',     '#339933'],
  ['white',     '#eeeeee'],
];

function renderEnergyBar(energyData, nbSources, bfElementId) {
  const bf = document.getElementById(bfElementId);
  if (!bf) return;
  const barId = bfElementId + '-energy-bar';
  let svg = document.getElementById(barId);
  if (!svg) {
    svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.id = barId;
    svg.classList.add('energy-bar');
    bf.appendChild(svg);
  }

  const total = energyData ? energyData.total : 0;
  const totalCircles = Math.max(total, nbSources);
  if (!totalCircles) {
    svg.style.display = 'none';
    return;
  }
  svg.style.display = '';

  const GAP = 2;
  const R = Math.max(4, Math.round((bf.clientWidth / 2 - 14 * GAP) / 30));
  const D = R * 2;
  svg.setAttribute('width', totalCircles * (D + GAP) - GAP);
  svg.setAttribute('height', D);
  while (svg.firstChild) svg.removeChild(svg.firstChild);

  const ns = 'http://www.w3.org/2000/svg';

  if (energyData) {
    const bd = energyData.breakdown || {};
    const parts = [`total energy: ${total}`];
    for (const [key] of ENERGY_COLOR_MAP) {
      if (bd[key] > 0) parts.push(`max ${bd[key]} ${key}`);
    }
    if ((bd.colorless || 0) > 0) parts.push(`max ${bd.colorless} colorless`);
    const title = document.createElementNS(ns, 'title');
    title.textContent = parts.join(', ');
    svg.appendChild(title);
  }

  const emptyCount = Math.max(0, nbSources - total);

  // Build per-circle color arrays, or flag for gradient rect (3+ mixed colors)
  const circleColors = [];
  let gradientRectColors = null;
  if (total > 0 && energyData && energyData.breakdown) {
    const bd = energyData.breakdown;
    const sumColored = ENERGY_COLOR_MAP.reduce((s, [k]) => s + (bd[k] || 0), 0);
    if (sumColored > total) {
      const nonzero = ENERGY_COLOR_MAP
        .map(([key, color]) => [color, Math.min(total, bd[key] || 0)])
        .filter(([, count]) => count > 0);
      if (nonzero.length === 1) {
        const [[color, count]] = nonzero;
        for (let i = 0; i < count; i++) circleColors.push([color]);
      } else if (nonzero.length === 2) {
        const [[color1, count1], [color2, count2]] = nonzero;
        const mix = count1 + count2 - total;
        for (let i = 0; i < count1 - mix; i++) circleColors.push([color1]);
        for (let i = 0; i < mix; i++) circleColors.push([color1, color2]);
        for (let i = 0; i < count2 - mix; i++) circleColors.push([color2]);
      } else {
        gradientRectColors = nonzero.map(([color]) => color);
      }
    } else {
      for (const [key, color] of ENERGY_COLOR_MAP) {
        for (let i = 0; i < (bd[key] || 0); i++) circleColors.push([color]);
      }
      while (circleColors.length < total) circleColors.push(['#aaaaaa']);
    }
  }

  const drawCircle = (idx, colors, stroke) => {
    const cx = idx * (D + GAP) + R, cy = R, innerR = R - 1;
    if (!colors) {
      const c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('r', innerR);
      c.setAttribute('fill', 'none');
      c.setAttribute('stroke', stroke); c.setAttribute('stroke-width', '1.5');
      svg.appendChild(c);
    } else if (colors.length === 1) {
      const c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('r', innerR);
      c.setAttribute('fill', colors[0]);
      svg.appendChild(c);
    } else {
      const n = colors.length;
      for (let i = 0; i < n; i++) {
        const a0 = (i / n) * 2 * Math.PI - Math.PI / 2;
        const a1 = ((i + 1) / n) * 2 * Math.PI - Math.PI / 2;
        const x1 = cx + innerR * Math.cos(a0), y1 = cy + innerR * Math.sin(a0);
        const x2 = cx + innerR * Math.cos(a1), y2 = cy + innerR * Math.sin(a1);
        const p = document.createElementNS(ns, 'path');
        p.setAttribute('d', `M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${innerR} ${innerR} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`);
        p.setAttribute('fill', colors[i]);
        svg.appendChild(p);
      }
    }
  };

  for (let i = 0; i < emptyCount; i++) drawCircle(i, null, '#888888');

  if (gradientRectColors) {
    const rectW = total * D + (total - 1) * GAP;
    const rectX = emptyCount * (D + GAP);
    const gradId = barId + '-mixgrad';
    const n = gradientRectColors.length;
    const BLUR = (R / 2) / rectW;
    const defs = document.createElementNS(ns, 'defs');
    const grad = document.createElementNS(ns, 'linearGradient');
    grad.id = gradId;
    gradientRectColors.forEach((color, i) => {
      const addStop = (offset, c) => {
        const s = document.createElementNS(ns, 'stop');
        s.setAttribute('offset', Math.min(1, Math.max(0, offset)));
        s.setAttribute('stop-color', c);
        grad.appendChild(s);
      };
      if (i === 0) addStop(0, color);
      else addStop(i / n + BLUR, color);
      if (i === n - 1) addStop(1, color);
      else addStop((i + 1) / n - BLUR, color);
    });
    defs.appendChild(grad);
    svg.appendChild(defs);
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('x', rectX); rect.setAttribute('y', 0);
    rect.setAttribute('width', rectW); rect.setAttribute('height', D);
    rect.setAttribute('rx', R); rect.setAttribute('ry', R);
    rect.setAttribute('fill', `url(#${gradId})`);
    svg.appendChild(rect);
  } else {
    for (let i = 0; i < circleColors.length; i++) drawCircle(emptyCount + i, circleColors[i], null);
  }
}

function renderBattlefield(snapshot, player, elementId) {
  let zone = document.getElementById(elementId);
  clearElement(zone);
  snapshot.battlefield
    .filter(permanent => permanent.controller_id === player.player_id)
    .forEach(permanent => {
      let element = cardElementFromSnapshot(permanent.card);
      setCardState(element, permanent.card, permanent);
      zone.appendChild(element);
    });
  const nbSources = snapshot.battlefield
    .filter(p => p.controller_id === player.player_id && p.types.includes('source'))
    .length;
  zone.dataset.nbSources = nbSources;
  renderEnergyBar(player.energy, nbSources, elementId);
}

function renderStack(snapshot) {
  let stack = document.getElementById('stack');
  clearElement(stack);
  snapshot.stack.forEach(item => {
    let element;
    if (item.card) {
      element = cardElementFromSnapshot(item.card);
    }
    else {
      element = document.createElement('div');
      element.className = 'card ability';
      element.id = item.stack_id;
      element.innerText = 'Effect';
    }
    stack.appendChild(element);
  });
}

function renderPlayerStats(player, prefix) {
  document.getElementById(`${prefix}-name`).innerText = player.name;
  document.getElementById(`${prefix}-life`).innerText = `Life: ${player.life}`;
  document.getElementById(`${prefix}-energy`).innerText = `Energy: ${player.energy.pool}`;
}

function renderQuestionFromSnapshot(snapshot) {
  let question = snapshot.question;
  let btn = document.getElementById('confirm');
  btn.innerText = "...";
  btn.disabled = true;
  clear_instruction();
  var arrow = document.getElementById('arrow');
  arrow.style.fill = "lightgrey";

  if (!question) {
    cleanupChooseActionUI();
    window.question = null;
    return;
  }

  if (question.player.is_me) {
    if (window.question && window.question.id === question.id) {
      cleanupFunctions[window.question.question]();
      window.question = null;
    }
    var pass_oc = pass_only_choice(question);
    var autopass = document.getElementById('autopass');
    if (autopass.checked && pass_oc) {
      window.setTimeout(send_answer, 1000, pass_oc);
    }
    else {
      build_question_ui(question);
    }
  }
  else {
    btn.innerText = "waiting for " + question.player.name;
    window.log_refresh_timeout_id = window.setTimeout(log_refresh, 200);
  }
}

function renderGameView(snapshot) {
  let me = playerBySeat(snapshot, true);
  let opponent = playerBySeat(snapshot, false);
  if (!me || !opponent) {
    return;
  }

  renderPlayerStats(me, 'my');
  renderPlayerStats(opponent, 'op');
  renderZone('hand', snapshot.zones[me.player_id].hand);
  renderZone('my-graveyard', snapshot.zones[me.player_id].graveyard);
  renderZone('op-graveyard', snapshot.zones[opponent.player_id].graveyard);
  document.getElementById('op-hand').innerText = `${opponent.hand_count} cards`;
  renderBattlefield(snapshot, me, 'bf-mine');
  renderBattlefield(snapshot, opponent, 'bf-theirs');
  renderStack(snapshot);
  indicate_step({
    step: snapshot.turn.step,
    active_player: {is_me: snapshot.turn.active_player_id === me.player_id}
  });
  renderQuestionFromSnapshot(snapshot);
}

function refreshGameView() {
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    if (httpRequest.status >= 400) {
      var newWindow = window.open('', '_blank');
      newWindow.document.write(httpRequest.responseText);
      return;
    }
    renderGameView(JSON.parse(httpRequest.responseText));
  });
  httpRequest.open("GET", GAME_VIEW_URI);
  httpRequest.send();
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
    animatedMove(getCardElement(event.permanent.card), tgt);
    write_message(`${event.permanent.card.name} enters the battlefield.`);
  },

  ExitTheBattlefieldEvent: function(event) {
    if (event.permanent.card.token) {
      let card = getCardElement(event.permanent.card);
      card.parentNode.removeChild(card);
    }
  },

  CreateContinuousEffectEvent: function(event) {
    console.log(event);
    const mod_text = {
      delta_stat: m => (m[1]<0?"":"+") + m[1] + "/" + (m[2]<0?"":"+") + m[2],
      add_keyword: m => m[1],
      remove_keyword: m => 'not ' + m[1],
      change_controller: () => 'controlled',
    };
    event.objects.forEach(obj => {
      let card = getCardElement(obj.card);
      let modifiers = card.children[1];
      event.modifiers.forEach(mod => {
        let element = document.createElement('div');
        element.innerText = (mod_text[mod[0]] || (m => m[0]))(mod);
        element.setAttribute('class', 'modifier ' + mod[0] + ' ' + event.effect_id);
        modifiers.appendChild(element);
      });
      console.log(obj.card.name);
    });
  },

  DamageEvent: function(event) {
    let card = getCardElement(event.permanent.card);
    let modifiers = card.children[1];
    let element = document.createElement('div');
    element.innerText = event.damage + ' damage';
    element.setAttribute('class', 'modifier damage');
    modifiers.appendChild(element);
  },

  EndContinuousEffectEvent: function(event) {
    var x = document.getElementsByClassName(event.effect_id);
    while (x[0]) {
      x[0].parentNode.removeChild(x[0]);
    }
  },

  ClearDamageEvent: function(event) {
    var x = document.getElementsByClassName('damage');
    while (x[0]) {
      x[0].parentNode.removeChild(x[0]);
    }
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

  StackEffectEvent: function(event) {
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
    let item = document.getElementById(stack_id);
    if (item) {
      stack.removeChild(item);
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
    const bfId = event.player.is_me ? 'bf-mine' : 'bf-theirs';
    const nbSources = parseInt(document.getElementById(bfId).dataset.nbSources || '0', 10);
    renderEnergyBar(event.new_energy, nbSources, bfId);
  },

  PayEnergyEvent: function(event) {
    document.getElementById(event.player.is_me ? 'my-energy' : 'op-energy')
            .innerText = `Energy: ${event.new_total}`;
    const bfId = event.player.is_me ? 'bf-mine' : 'bf-theirs';
    const nbSources = parseInt(document.getElementById(bfId).dataset.nbSources || '0', 10);
    renderEnergyBar(event.new_energy, nbSources, bfId);
  },

  ClearPoolEvent: function(event) {
    document.getElementById(event.player.is_me ? 'my-energy' : 'op-energy')
            .innerText = "Energy: {0}";
    const bfId = event.player.is_me ? 'bf-mine' : 'bf-theirs';
    const nbSources = parseInt(document.getElementById(bfId).dataset.nbSources || '0', 10);
    renderEnergyBar({total: 0, breakdown: {}}, nbSources, bfId);
  },

  PlayerDamageEvent: function(event) {
    write_message(`${event.player.name} received ${event.damage} damage.`);
    var element = document.getElementById(event.player.is_me ? 'my-life' : 'op-life');
    element.innerText = `Life: ${event.new_total}`;
    element.classList.add('hit');
    window.setTimeout( () => element.classList.remove('hit'), 0);
  },

  StepEvent: function(event) {
    indicate_step(event);
    ['playable', 'discardable', 'activateable', 'selectable',
     'placeholder', 'inmotion'].forEach(
       className => Array.from(document.getElementsByClassName(className)).forEach(
         element => element.classList.remove(className)));
    if (event.step == 'BEGIN_COMBAT') {
      let combat = document.getElementById('combat');
      combat.innerHTML = '';
      if (event.active_player.is_me) {
        combat.classList.remove('opponent-attacking');
      } else {
        combat.classList.add('opponent-attacking');
      }
      attackers = {};
      blockers = {};
    }
    if (event.step == 'POSTCOMBAT_MAIN') {
      forEachKeyValue(attackers, (key, attacker) => attacker.destroy());
      attackers = null;
    }
  },

  AttackEvent: function(event) {
    write_message(`${event.attacker.card.name} attacks ${event.player.name}.`);
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
    forEachKeyValue(event.blockers, (id, evt_blocker) => {
      blocker = blockers[evt_blocker.card.card_id];
      if (!blocker) {
        blocker = Blocker(evt_blocker.card.card_id);
        blockers[evt_blocker.card.card_id] = blocker;
        attacker.addBlocker(blocker, event.attacker.card.card_id);
      }
      blocker.block(event.attacker.card.card_id);
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
    if (httpRequest.status == 409) {
      // Todo remove when issue #10 is fixed
      console.log(httpRequest);
    }
    else if (httpRequest.status >= 400) {
      var newWindow = window.open('', '_blank');
      newWindow.document.write(httpRequest.responseText);
    }
    result = JSON.parse(httpRequest.responseText);
    result.event_log.forEach(handleGameEvent);
    refreshGameView();
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
    cardElement.classList.add('selectable');
    cardElement.setAttribute('style', '');
    var placeholderElement = cardElement.cloneNode(true);
    placeholderElement.classList.add('placeholder');

    placeholderElement.id += "_blocking_" + card_id;
    blockerDiv.appendChild(placeholderElement);
    blocker.placeholders[choice_id] = placeholderElement;

    function click() {
      if (blocker.blocking() === choice_id) {
        blocker.block("noblock");
      }
      else {
        blocker.block(choice_id);
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

function Blocker(card_id, action_id) {
  var placeholders = {};
  var blocking = 'noblock';
  var cardElement = document.getElementById(card_id);

  function block(choice_id) {
    forEachKeyValue(placeholders, function(ch_id, element) {
      if (ch_id === choice_id) {
        element.classList.remove('placeholder');
      }
      else {
        element.classList.add('placeholder');
      }
    });
    if (choice_id === 'noblock') {
      cardElement.classList.remove('placeholder');
    }
    else {
      cardElement.classList.add('placeholder');
    }
    blocking = choice_id;
  }

  return {
    placeholders: placeholders,
    blocking: function() {return blocking;},
    card_id: card_id,
    action_id: action_id,
    cardElement: cardElement,
    block: block,
  };
}

function build_question_ui(question){
  if (window.question && window.question.id === question.id) {
    // this question is already setup
    return;
  }
  cleanupChooseActionUI();
  window.question = question;
  messages = {
    action: "Choose an action (click on a highlighted card) or pass (click on the dial)",
    target: "Choose the target",
    discard: "Choose a card from your hand to discard"
  };
  write_instruction(messages[question.reason]);
  var choices = document.getElementById('choices');
  var arrow = document.getElementById('arrow');
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
        arrow.style.fill = "lightgreen";
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
      if (action.action == 'target') {
        let card;
        if (action.type === 'player') {
          let is_me = (action.player == question.player.name && question.player.is_me);
          card = document.getElementById(is_me ? 'my-avatar' : 'op-avatar');
        }
        else {
          card = document.getElementById(action.card_id);
        }
        card.classList.add('selectable');
        card.onclick = makeOnclick(action_id);
      }
      if (action.action == 'choose_x') {
        let menu = document.getElementById('choose_x');
        if (!menu) {
          menu = document.createElement('div');
          menu.setAttribute('id', 'choose_x');
          menu.setAttribute('class', 'menu');
          document.body.appendChild(menu);
        }
        let button = document.createElement('button');
        button.appendChild(document.createTextNode('Choose X = ' + action.value));
        var makeOnclick2 = function(action_id) {
          return function () {
            send_answer(action_id);
            menu.parentNode.removeChild(menu);
          };
        };
        button.onclick = makeOnclick2(action_id);
        menu.appendChild(button);
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
    write_instruction("Declare your attackers and confirm by clicking on the turn indicator.");
    make_ans_button("Skip Attack", get_and_send_answer);
    arrow.style.fill = "orange";
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
    write_instruction("Declare your blockers and confirm by clicking on the turn indicator.");
    make_ans_button("Confirm Blockers", get_and_send_answer);
    arrow.style.fill = "orange";
    blockers = {};
    var count = 0;
    forEachKeyValue(question.choices, (action_id, action) => {
      count += 1;
      forEachKeyValue(action.attackers, (attacker_id, attacker) => {
        blocker = blockers[action.candidate.card.card_id];
        if (!blocker) {
          blocker = Blocker(action.candidate.card.card_id, action_id);
          blockers[action.candidate.card.card_id] = blocker;
        }
        attackers[attacker.card.card_id].addBlocker(blocker, attacker_id);
      });
    });
  }
  else if (question.question == 'OrderBlockers') {
    // TODO: Let the user order the blockers.
    var answer = {};
    forEachKeyValue(question.choices, (action_id, action) => {
      answer[action_id] = Object.getOwnPropertyNames(action.blockers);
    });
    send_answer(answer);
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
      if (!card) return;
      card.classList.remove('playable');
      card.removeAttribute('onclick');
    }
    if (action.action == 'discard') {
      let card = document.getElementById(action.card_id);
      if (!card) return;
      card.classList.remove('discardable');
      card.removeAttribute('onclick');
    }
    if (action.action == 'activate') {
      let card = document.getElementById(action.card_id);
      if (!card) return;
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
    forEachKeyValue(blockers, (card_id, blocker) => {
      if (blocker.blocking() != 'noblock') answer[blocker.action_id] = blocker.blocking();
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
  clear_instruction();
  return answer;
}


function send_answer (answer) {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `${game_uri}/answer`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.addEventListener("load", function(){
    if (httpRequest.status == 409) {
      // Todo remove when issue #10 is fixed
      console.log(httpRequest);
    }
    else if (httpRequest.status >= 400) {
      var newWindow = window.open('', '_blank');
      newWindow.document.write(httpRequest.responseText);
    }
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

function animatedMove(element, target, delay=300){
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
  let div = document.getElementById('stepdial');
  btn.disabled = false;
  btn.innerText = label;
  btn.onclick = onclick;
  div.onclick = onclick;
}

function write_instruction(text){
  let div = document.getElementById('instruction');
  div.innerText = text;
  div.classList.add('active');
}

function clear_instruction(){
  let div = document.getElementById('instruction');
  div.innerHTML = '';
  div.classList.remove('active');
}

function savegame() {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `${game_uri}/save`);
  httpRequest.send();
}
