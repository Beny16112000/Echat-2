from flask import Flask, redirect, render_template, request, url_for
from flask_socketio import SocketIO, join_room
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from db import get_user, save_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, get_room_members, is_room_admin, update_room, remove_room_members, save_message, get_messages


app = Flask(__name__)
app.secret_key = 'Not so secret'
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)



@app.route("/", methods=['GET', 'POST'])
def index():
    """
    Home Page
    """
    rooms = []
    if current_user.is_authenticated:
        rooms = get_rooms_for_user(current_user.username)
    return render_template('index.html', rooms=rooms)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login
    """
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user(username)
        login_user(user)
        return redirect('/')
    return render_template('login.html')


@app.route("/logout")
@login_required
def logout():
    """
    Logout
    """
    logout_user()
    return redirect('/')



@app.route("/register", methods=['GET', 'POST'])
def register ():
    """
    Register Page
    """
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        save_user(username,email,password)
        return redirect('/')
    return render_template('register.html')


@app.route("/rooms/<room_id>")
@login_required
def view_room(room_id):
    """
    Chat page
    """
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        rooms_members = get_room_members(room_id)
        messages = get_messages(room_id)
        return render_template('chat.html', room=room, rooms_members=rooms_members, username=current_user.username, messages=messages)
    else:
        return 'room not found', 404


@app.route("/create-room", methods=['GET', 'POST'])
@login_required
def create_room():
    """
    Create Room Function
    """
    message = ''
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        usernames = [username.strip() for username in request.form.get('members').split(',')]
        if len(room_name) and len(usernames):
            room_id = save_room(room_name, current_user.username)
            if current_user.username in usernames:
                usernames.remove(current_user.username)
            add_room_members(room_id, room_name, usernames, current_user.username)
            return redirect(url_for('/view-room', room_id=room_id))
        else:
            message = 'Filed to create room'
    return render_template('create_room.html', message=message)


@app.route("/rooms/<room_id>/edit", methods=['GET', 'POST'])
def edit_room(room_id):
    """
    Edit Room 
    """
    room = get_room(room_id) 
    if room and is_room_admin(room_id, current_user.username):
        current_room_members =  [member['_id']['username'] for member in get_room_members(room_id)]
        if request.method == 'POST':
            room_name = request.form.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)
            members_to_remove = request.form.get('members')
            members_to_remove = list(members_to_remove)
            remove_room_members(room_id, members_to_remove)
        room_members_str = ",".join(current_room_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str)
    else:
        return 'Room not fount', 404    


@socketio.on('send_message')
def hendle_send_message_event(data):
    """
    When someone sent message in the room.
    """
    app.logger.info("{} has send message to the room {}: {}".format(data['username'], data['room'], data['message']))
    save_message(data['room'],data['message'],data['username'])
    socketio.emit('receive_message', data, room=data['room'])


@socketio.on('join_room')
def handle_join_room_event(data):
    app.logger.info("{} has joined the room {}".format(data['username'], data['room']))
    join_room(data['room'])
    socketio.emit('join_room_announcement', data)

@login_manager.user_loader
def load_user(username):
    return get_user(username)


if __name__ == "__main__":
    socketio.run(app, debug=True)