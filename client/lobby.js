function send_msg() {
  let chat_msg = document.getElementById('chat_msg');
  var httpRequest = new XMLHttpRequest();
  httpRequest.open("POST", `/chat_msg`);
  httpRequest.send(chat_msg.value);
  chat_msg.value = '';
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
        users.appendChild(element);
      }
      element.innerText = usr.user;
      element.className = `user-${usr.status}`;
    });
    for (var element of obsolete) {
      users.removeChild(element);
    }
  });
  httpRequest.open("GET", `/lobby_users`);
  httpRequest.send();
  window.setTimeout(update_users, 5000);
}

read_msg();
update_users();
