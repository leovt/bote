deck = {};

function add_card(art_id) {
  if (deck.hasOwnProperty(art_id)) {
    deck[art_id] += 1;
  }
  else {
    deck[art_id] = 1;
    let card = document.createElement('div');
    card.id = `card${art_id}`;
    card.className = "deck_card";
    let plus = document.createElement('button');
    plus.innerText="+";
    plus.setAttribute('onclick', `add_card(${art_id})`);
    let minus = document.createElement('button');
    minus.innerText="-";
    minus.setAttribute('onclick', `remove_card(${art_id})`);
    let img = document.createElement('img');
    img.src=`/card/svg/${art_id}`;
    img.className = "card";
    let count = document.createElement('span');
    count.id = `count${art_id}`;
    card.appendChild(img);
    card.appendChild(document.createElement('br'));
    card.appendChild(minus);
    card.appendChild(count);
    card.appendChild(plus);
    document.getElementById('deck').appendChild(card);
  }
  document.getElementById(`count${art_id}`).innerText=deck[art_id];
}

function remove_card(art_id) {
  if (deck.hasOwnProperty(art_id)) {
    deck[art_id] -= 1;
    document.getElementById(`count${art_id}`).innerText=deck[art_id];
    if (deck[art_id] <= 0) {
      document.getElementById('deck').removeChild(
        document.getElementById(`card${art_id}`));
      delete deck[art_id];
    }
  }
}

function save_deck() {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", document.URL);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.addEventListener("load", function(){});
  httpRequest.send(JSON.stringify({
    name: document.getElementById('name').value,
    cards: deck
  }));
}
