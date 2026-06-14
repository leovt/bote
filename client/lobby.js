function send_msg() {
  let chat_msg = document.getElementById('chat_msg');
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `/chat_msg`);
  httpRequest.send(chat_msg.value);
  chat_msg.value = '';
}

function logHttpError(context, httpRequest) {
  console.error(
    `${context} failed with HTTP ${httpRequest.status}`,
    httpRequest.responseText || httpRequest
  );
}

function save_name() {
  let input = document.getElementById('display-name');
  return save_display_name(input.value);
}

function save_display_name(name, onSuccess, onError) {
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `/session/name`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.addEventListener("load", function () {
    if (httpRequest.status >= 400) {
      if (onError) onError();
      return;
    }
    var result = JSON.parse(httpRequest.responseText);
    document.getElementById('display-name').value = result.display_name;
    if (onSuccess) onSuccess(result.display_name);
  });
  httpRequest.addEventListener("error", function () {
    if (onError) onError();
  });
  httpRequest.send(JSON.stringify({name: name}));
}

function create_invite() {
  var game_window = window.open('', '_blank');
  game_window.document.write('Creating invite ...');
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    if (httpRequest.status >= 400) {
      logHttpError('create_invite', httpRequest);
      game_window.close();
      return;
    }
    var result = JSON.parse(httpRequest.responseText);
    game_window.location.href = result.url;
  });
  httpRequest.open("POST", `/game/invite`);
  httpRequest.send();
}


function duel(username) {
  var game_window = window.open('', '_blank');
  game_window.document.write('Loading game ...');
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    if (httpRequest.status >= 400) {
      logHttpError('duel', httpRequest);
      game_window.close();
      return;
    }
    game_window.location.href = httpRequest.getResponseHeader('Location');
  });
  httpRequest.open("POST", `/game/create`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.send(JSON.stringify({
    opponent: username
  }));
}

function challenge(playerId) {
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    if (httpRequest.status === 409) {
      logHttpError('challenge', httpRequest);
      return;
    }
    if (httpRequest.status >= 400) {
      logHttpError('challenge', httpRequest);
      return;
    }
    alert('Challenge sent.');
  });
  httpRequest.open("POST", `/challenge`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.send(JSON.stringify({target: playerId}));
}


msg_count = 0;

function read_msg() {
  var chat = document.getElementById('chat');
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    var result = JSON.parse(httpRequest.responseText);
    result.forEach(function(msg) {
      msg_count += 1;
      let element = document.createElement('li');
      let user = document.createElement('div');
      user.innerText = msg.user;
      user.className = 'chat_user';
      let message = document.createElement('div');
      message.innerText = msg.message;
      message.className = 'chat_message';
      element.appendChild(user);
      element.appendChild(message);
      chat.appendChild(element);
      chat.scrollTop = chat.scrollHeight;
    });
  });
  httpRequest.open("GET", `/chat_msg?first=${msg_count}`);
  httpRequest.send();
  window.setTimeout(read_msg, 500);
}

function update_users() {
  // Update the User List
  var users = document.getElementById('users');
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    var obsolete = new Set(Array.from(users.children).map(el => el.id));
    var result = JSON.parse(httpRequest.responseText);
    result.forEach(function(usr) {
      let element_id = `user-${usr.player_id}`;
      let element = document.getElementById(element_id);
      if (element) {
        obsolete.delete(element_id);
        element.querySelector('.user-name').textContent = usr.user;
      } else {
        element = document.createElement('li');
        element.id = element_id;
        var nameSpan = document.createElement('span');
        nameSpan.className = 'user-name';
        nameSpan.textContent = usr.user;
        element.appendChild(nameSpan);
        if (!usr.is_me) {
          var button = document.createElement('button');
          button.innerText = "Challenge";
          button.addEventListener('click', function () {
            challenge(usr.player_id);
          });
          element.appendChild(button);
        }
        users.appendChild(element);
      }
      element.className = `user-${usr.status}`;
    });
    for (var element_id of obsolete) {
      if (element_id) {
        var element = document.getElementById(element_id);
        if (!element.classList.contains("robot_user")) {
          users.removeChild(element);
        }
      }
    }
  });
  httpRequest.open("GET", `/lobby_users`);
  httpRequest.send();

  // Update the Game List
  var games = document.getElementById('games');
  var httpRequest2 = new XMLHttpRequest();
  httpRequest2.addEventListener("load", function () {
    games.innerHTML = "";
    var result = JSON.parse(httpRequest2.responseText);
    result.forEach(function(game) {
        var element = document.createElement('li');
        var anchor = document.createElement('a');
        anchor.href = game.url;
        anchor.innerText = game.players.join(" vs. ");
        anchor.target = '_blank';
        element.appendChild(anchor);
        element.appendChild(document.createTextNode(`(${game.status})`));
        games.appendChild(element);
    });
  });
  httpRequest2.open("GET", `/games`);
  httpRequest2.send();
  window.setTimeout(update_users, 500);
}

function check_challenges() {
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    var result = JSON.parse(httpRequest.responseText);
    result.incoming.forEach(function(challenge) {
      var accepted = confirm(`${challenge.from} challenged you. Accept?`);
      var responseRequest = new XMLHttpRequest();
      responseRequest.open("POST", `/challenge/${challenge.id}/respond`);
      responseRequest.setRequestHeader('Content-Type', 'application/json');
      responseRequest.addEventListener("load", function () {
        if (responseRequest.status >= 400) {
          logHttpError('respond_challenge', responseRequest);
          return;
        }
        if (accepted && responseRequest.status < 400) {
          window.open(JSON.parse(responseRequest.responseText).table_url, '_blank');
        }
      });
      responseRequest.send(JSON.stringify({response: accepted ? 'accept' : 'decline'}));
    });
    result.outgoing.forEach(function(challenge) {
      let seenKey = `challenge-${challenge.id}-${challenge.status}`;
      if (sessionStorage.getItem(seenKey)) {
        return;
      }
      sessionStorage.setItem(seenKey, '1');
      if (challenge.status === 'accepted') {
        window.open(challenge.table_url, '_blank');
      } else {
        alert(`${challenge.target} ${challenge.status} your challenge.`);
      }
    });
  });
  httpRequest.open("GET", `/challenges`);
  httpRequest.send();
  window.setTimeout(check_challenges, 500);
}

document.getElementById('display-name').addEventListener('keyup', function(event) {
  if (event.keyCode === 13) {
    save_name();
  }
});
document.getElementById('display-name').addEventListener('blur', save_name);

var nameOverlay = document.getElementById('name-overlay');
if (nameOverlay) {
  var overlayForm = document.getElementById('name-overlay-panel');
  var overlayInput = document.getElementById('overlay-display-name');
  var overlayError = document.getElementById('name-overlay-error');
  overlayForm.addEventListener('submit', function (event) {
    event.preventDefault();
    var name = overlayInput.value.trim();
    if (!name) {
      overlayError.textContent = 'Please enter a name.';
      overlayInput.focus();
      return;
    }
    save_display_name(name, function () {
      nameOverlay.remove();
    }, function () {
      overlayError.textContent = 'Could not save the name. Please try again.';
    });
  });
  overlayInput.focus();
}

read_msg();
update_users();
check_challenges();

function loadsaved(filename) {
  var game_window = window.open('', '_blank');
  game_window.document.write('Loading game ...');
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `/game/load`);
  httpRequest.addEventListener("load", function () {
    if (httpRequest.status >= 400) {
      logHttpError('loadsaved', httpRequest);
      game_window.close();
      return;
    }
    game_window.location.href = httpRequest.getResponseHeader('Location');
  });
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.send(JSON.stringify({
    filename: filename
  }));
}
