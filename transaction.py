import os

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter
from dotenv import load_dotenv

load_dotenv()

class Transaction:
    def __init__(self, activity, amount, description, timestamp, type, bank='Banco de Chile', doc=None, user=None):
        self.activity = activity
        self.amount = amount
        self.description = description
        self.timestamp = timestamp
        self.type = type
        self.bank = bank
        self.doc = doc
        self.user = user
        self.reference_set = None
        Firebase()
        self.client = firestore.client()

    @staticmethod
    def from_dict(source):
        return Transaction(source['activity'],
                           source['amount'],
                           source['description'],
                           source['timestamp'],
                           source.get('type'),
                           'Banco de Chile',
                           source.get('doc'),
                           source.get('user'))

    def to_dict(self):
        return {'activity': self.activity,
                'amount': self.amount,
                'description': self.description,
                'timestamp': self.timestamp,
                'type': self.type,
                'bank': self.bank}

    def __repr__(self):
        return f"actividad: {self.activity}, \nmonto: {self.amount}, \ncomercio: {self.description}, \nfecha: {self.timestamp}, \ntipo: {self.type}, \nbanco: {self.bank} "

    def persisted(self):
        tr = self.reference()
        return len(tr) > 0

    def reference(self):
        self.reference_set = self.firebase_collection().where(filter=FieldFilter("activity", "==", self.activity)). \
            where(filter=FieldFilter("description", "==", self.description)). \
            where(filter=FieldFilter("timestamp", "==", self.timestamp)).get() if self.reference_set is None else self.reference_set
        return self.reference_set

    def reference_dict(self):
        return self.reference()[0].to_dict()

    def persist(self):
        tr_persisted = self.persisted()
        if tr_persisted and self.reference_dict().get('type') is None:
            return self.update_type()
        if not tr_persisted:
            # Push the data dictionary to the database
            to_add = self.to_dict()
            to_add.update({'category': None})
            return self.firebase_collection().add(to_add)

    def update_type(self):
        return self.reference()[0].reference.set({"type": self.type}, merge=True)

    def update_bank(self):
        return self.reference()[0].reference.set({"bank": self.bank}, merge=True)

    def firebase_collection(self):
        return self.client.collection('users').document(self.user).collection("transactions")


class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Firebase(metaclass=SingletonMeta):
    def __init__(self):
        cred = credentials.Certificate(os.environ['CREDENTIAL_PATH'])
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://money-tracker-418ab-default-rtdb.firebaseio.com'
        })
