from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')
mongodb_with_srv = os.environ.get('MONGODB_WITH_SRV')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

mongodb_protocol = 'mongodb+srv' if mongodb_with_srv == 'true' else 'mongodb'

if mongodb_username and mongodb_password:
    url = f"{mongodb_protocol}://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"{mongodb_protocol}://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

print(f"MongoDB connection established")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health")
def health():
    return jsonify(dict(status="OK")), 200

@app.route("/count")
def count():
    """
    Count the number of songs in the database
    """
    count = db.songs.count_documents({})
    return {"count": count}, 200

@app.route("/song", methods=["GET"])
def songs():
    """
    Get all songs in the database
    """
    songs = db.songs.find({})
    return jsonify({"songs": parse_json(list(songs))}), 200

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """
    Get a song by id
    """
    song = db.songs.find_one({"id": id})
    print(song)
    if not song:
        return jsonify({"error": "Song not found"}), 404
    return jsonify({"song": parse_json(song)}), 200

@app.route("/song", methods=["POST"])
def add_song():
    """
    Add a song to the database
    """
    data = request.get_json()
    
    if db.songs.find_one({"id": int(data.get("id"))}):
        return jsonify({"Message": f"song with id {data['id']} already present"}), 302

    result = db.songs.insert_one(data)
    return jsonify({"id": str(result.inserted_id)}), 201


@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """
    Update a song in the database
    """
    data = request.get_json()
    old_song = db.songs.find_one({"id": id})

    if not old_song:
        return {"message": "Song not found"}, 404
    # check if same
    if old_song.get("id") == id and \
            old_song.get("title") == data.get("title") and \
            old_song.get("lyrics") == data.get("lyrics"):
        return {"message": "song found, but nothing updated"}, 200

    result = db.songs.update_one({"id": id}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"message": "Song not found"}), 404
    
    # check if same
    if old_song == get_song_by_id(id):
        return jsonify({"message": "No changes made"}), 304
    
    return jsonify(parse_json(db.songs.find_one({"id": id})))


@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """
    Delete a song from the database
    """
    result = db.songs.delete_one({"id": id})
    if result.deleted_count == 0:
        return jsonify({"message": "Song not found"}), 404
    return jsonify({"message": "Song deleted"}), 204