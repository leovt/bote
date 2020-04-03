function send_msg() {
  let chat_msg = document.getElementById('chat_msg');
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `/chat_msg`);
  httpRequest.send(chat_msg.value);
  chat_msg.value = '';
}


function duel(username) {
  var game_window = window.open('', '_blank');
  game_window.document.write('Loading game ...');
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    game_window.location.href = httpRequest.getResponseHeader('Location');
  });
  httpRequest.open("POST", `/game/create`);
  httpRequest.setRequestHeader('Content-Type', 'application/json');
  httpRequest.send(JSON.stringify({
    opponent: username
  }));
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
  window.setTimeout(read_msg, 1000);
}

function update_users() {
  // Update the User List
  var users = document.getElementById('users');
  var httpRequest = new XMLHttpRequest();
  httpRequest.addEventListener("load", function () {
    var obsolete = new Set(Array.from(users.children).map(el => el.id));
    var result = JSON.parse(httpRequest.responseText);
    result.forEach(function(usr) {
      let element_id = `user-${usr.user}`;
      let element = document.getElementById(element_id);
      if (element) {
        obsolete.delete(element_id);
      }
      else {
        element = document.createElement('li');
        element.id = element_id;
        element.innerText = usr.user;
        if (!usr.is_me) {
          button = document.createElement('button');
          button.innerText = "Duel";
          button.setAttribute('onclick', `duel('${usr.user}')`);
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
  window.setTimeout(update_users, 5000);
}

read_msg();
update_users();
