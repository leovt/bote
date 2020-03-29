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
    result = JSON.parse(httpRequest.responseText);
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
    });
  });
  httpRequest.open("GET", `/chat_msg?first=${msg_count}`);
  httpRequest.send();
  window.setTimeout(read_msg, 1000);
}

read_msg();
