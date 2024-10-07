import datetime
from dotenv import load_dotenv
import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from flask_cors import CORS

# Import models
from models import db, User, Goal, Group

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = 'BellaEOpisicaGrasa2000'  # Change this to a strong secret key

# Update CORS configuration to allow specific methods without preflight
CORS(app, resources={r"/*": {
    "origins": "*", 
    "methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True
}})

db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize the database
with app.app_context():
    db.create_all()  # Ensure all tables are created

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User Signup
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'message': 'Missing required fields'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists'}), 400

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    # Log in the user
    login_user(new_user)  # Log in the newly created user
    return jsonify({'message': 'User created and logged in successfully!'}), 201

# User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    print("Received login data:", data)  # For debugging, remove in production
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Missing username or password"}), 400

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }), 200
    return jsonify({"message": "Invalid username or password"}), 401

# Add a new route to check authentication status
@app.route('/check-auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            }
        }), 200
    else:
        return jsonify({"authenticated": False}), 401

# User Logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful!'}), 200

# Create a Goal
@app.route('/goals', methods=['POST'])
@login_required
def create_goal():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    deadline = data.get('deadline')
    group_id = data.get('group_id')  # Get the group_id if provided
    user_id = current_user.id  # User ID to associate the goal with a user

    if not title or user_id is None:
        return jsonify({'message': 'Missing title or user_id'}), 400

    # Check if the user exists
    user = current_user.id
    if user is None:
        return jsonify({'message': 'User not found'}), 404

    # Create the new goal
    new_goal = Goal(
        title=title,
        description=description,
        deadline=deadline if deadline else None,  # Allow deadline to be None if not provided
        completed=False,
        user_id=user_id,
        group_id=group_id  # Associate with the group if provided
    )
    db.session.add(new_goal)
    db.session.commit()

    return jsonify({
        'message': 'Goal created successfully!',
        'goal': new_goal.to_dict()  # Call the updated to_dict() method
    }), 201

# Get all Goals
@app.route('/goals', methods=['GET'])
@login_required  # Make sure this endpoint requires authentication
def get_goals():
    user_id = current_user.id  # Optional user ID to filter goals by user

    # Retrieve goals for the user, whether personal or group-related
    goals = Goal.query.filter((Goal.user_id == user_id) | (Goal.group_id.isnot(None))).all()

    return jsonify([goal.to_dict() for goal in goals]), 200
 
# Update a Goal
@app.route('/goals/<int:goal_id>', methods=['PUT'])
@login_required
def update_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)  # Get the goal or return 404 if not found

    # Check if the user is part of the group that shares the goal
    if goal.group_id and current_user not in goal.group.members:
        return jsonify({'message': 'You are not authorized to update this goal.'}), 403

    data = request.get_json()
    if 'completed' in data:
        goal.completed = data['completed']  # Update the completed status

    db.session.commit()  # Save changes to the database

    return jsonify({'message': 'Goal updated successfully!', 'goal': {
        'id': goal.id,
        'title': goal.title,
        'description': goal.description,
        'deadline': goal.deadline,
        'completed': goal.completed,
        'user_id': goal.user_id,
        'group_id' : goal.group_id  # Associate with the group if provided

    }}), 200
    
    
# Remove a Goal
@app.route('/goals/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)  # Get the goal or return 404 if not found

    # Only allow the owner of the goal to delete it
    if goal.user_id != current_user.id:
        return jsonify({'message': 'You are not authorized to delete this goal.'}), 403

    db.session.delete(goal)  # Delete the goal
    db.session.commit()  # Commit the changes to the database

    return jsonify({'message': 'Goal deleted successfully!'}), 200

# Create a Group
@app.route('/groups', methods=['POST'])
@login_required
def create_group():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({'message': 'Group name is required'}), 400

    new_group = Group(name=name, description=description)
    db.session.add(new_group)
    db.session.commit()

    # Automatically add the creator to the group
    new_group.members.append(current_user)
    db.session.commit()

    return jsonify({'message': 'Group created successfully!', 'group': {'id': new_group.id, 'name': new_group.name}}), 201

# Join a Group
@app.route('/groups/join/<int:group_id>', methods=['POST'])
@login_required
def join_group(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Add the user to the group
    if current_user not in group.members:
        group.members.append(current_user)
        db.session.commit()
        return jsonify({'message': 'You have joined the group!'}), 200
    else:
        return jsonify({'message': 'You are already a member of this group.'}), 400

# Get All Groups
@app.route('/groups', methods=['GET'])
def get_groups():
    groups = Group.query.all()
    return jsonify([{
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'members': [{'id': user.id, 'username': user.username} for user in group.members]  # Include members
    } for group in groups]), 200
    
# Get user's group   
@app.route('/groups/mine', methods=['GET'])
@login_required
def get_user_groups():
    # Fetch groups where the user is a member
    groups = current_user.groups  # This uses the relationship defined in the User model

    return jsonify([{
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'members': [{'id': member.id, 'username': member.username} for member in group.members]
    } for group in groups]), 200


# Join a Group
@app.route('/groups/<int:group_id>/join', methods=['POST'])
@login_required
def join_group_by_id(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Add the user to the group
    if current_user not in group.members:
        group.members.append(current_user)
        db.session.commit()
        return jsonify({'message': 'You have joined the group!'}), 200
    else:
        return jsonify({'message': 'You are already a member of this group.'}), 400

# Leave a Group
@app.route('/groups/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Remove the user from the group
    if current_user in group.members:
        group.members.remove(current_user)
        db.session.commit()
        return jsonify({'message': 'You have left the group!'}), 200
    else:
        return jsonify({'message': 'You are not a member of this group.'}), 400


# Run the application
if __name__ == '__main__':
    app.run(debug=True)
