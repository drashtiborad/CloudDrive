from datetime import datetime

from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from flaskmod import app, db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date_of_birth = db.Column(db.Date(), nullable=False)
    phone_number = db.Column(db.BigInteger, nullable=False)
    image_file = db.Column(db.String(1024), nullable=False, default='default.png')
    password = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow())
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow())

    def get_token(self, expires_sec=900):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({"user_id": self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return "User[{}, {}, {}, {}]".format(self.username, self.email, self.date_of_birth, self.phone_number)


class File(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    child_path = db.Column(db.String(255))
    parent_path = db.Column(db.String(255), default="/home/", nullable=False)
    type = db.Column(db.String(30))
    original_path = db.Column(db.String(255), default="/home/ubuntu/data")
    filename = db.Column(db.String(1024), nullable=False)
    size = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow())
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow())
    deleted_at = db.Column(db.DateTime())
    user = db.relationship(User)

    def __repr__(self):
        return "File[{},{},{}]".format(self.user_id, self.type, self.size)
