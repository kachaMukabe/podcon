from flask import abort, Flask, jsonify, request, render_template, render_template_string
from flask_sqlalchemy import SQLAlchemy
from os import environ
from rev_ai import apiclient
from dotenv import load_dotenv

import symbl
import time
import podcastindex
import pprint
import requests

load_dotenv()

access_token = environ.get("REV_ACCESS_TOKEN")

config = {
        "api_key": environ.get("API_KEY"),
        "api_secret": environ.get("API_SECRET") 
}

client = apiclient.RevAiAPIClient(access_token)


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)


class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    episode_id = db.Column(db.Integer)
    conversation_id = db.Column(db.String(40))
    rev_job_id = db.Column(db.String(40))
    episode_url = db.Column(db.String(120))

    def __init__(self, episode_id, episode_url):
        self.episode_id = episode_id
        self.episode_url = episode_url

    def __repr__(self):
        return f"Podcast {self.episode_id}"

def read_db(episode_id):
    episode = Podcast.query.filter_by(episode_id=episode_id).first()
    return episode

def save_conversation(episode_id, url, conversation=None, rev_job_id=None, podcast=None):
    if not podcast:
        podcast = Podcast(episode_id, url)
    if conversation:
        podcast.conversation_id = conversation.get_conversation_id()
    if rev_job_id:
        podcast.rev_job_id = rev_job_id
    db.session.add(podcast)
    db.session.commit()


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/search', methods=["GET"])
def search():
    query = request.args.get('search')
    index = podcastindex.init(config)
    result = index.search(query)
    templ = """
        <progress id="indicator" class="htmx-indicator progress is-large is-info" max="100">60%</progress>
        <div class="columns">
    {% for pod in podcasts %}
    <div class="column is-half">
        <div class="card block">
            <div class="card-content">
                <div class="media">
                    <div class="media-left">
                        <figure class="image is-48x48">
                            <img src="{{ pod.image }}"
                        </figure>
                    </div>
                    <div class="media-content">
                        <p class="title is-4">{{ pod.title }}</p>
                        <p class="subtitle is-6"> {{ pod.author }}</p>
                    </div>
                </div>
                <div class="content">
                    {{ pod.description }}
                </div>
            </div>
            <footer class="card-footer">
                <a class="card-footer-item" hx-indicator="#indicator" hx-get="/episodes/{{pod.id}}" hx-target="#search-results">Get episodes</a>
            </footer>
        </div>
    </div>
    {% endfor %}
    </div>
    """
    podcasts = result['feeds']
    return render_template_string(templ, podcasts=podcasts)

@app.route('/episodes/<id>')
def episodes(id):
    index = podcastindex.init(config)
    result = index.episodesByFeedId(id)
    pprint.pprint(result['items'][0])
    url = result['items'][0]['enclosureUrl']
    templ = """
    <table class="table">
        <thead>
            <tr>
                <th>Title</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
        {% for episode in episodes %}
            <tr>
                <td>{{ episode.title }}</td>
                <td>
                    <form action="/episode" method="POST">
                        <input hidden name="url" value="{{ episode.enclosureUrl }}">
                        <input hidden name="episode_id" value="{{ episode.id }}">
                        <input type="submit" value="Go to episode" class="button">
                    </form>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    """
    episodes = result['items']
    return render_template_string(templ, episodes=episodes)

@app.route('/episode', methods=["POST"])
def episode_detail():
    episode_id = request.form.get("episode_id")
    print(episode_id)
    url = request.form.get("url")
    print(url)
    return render_template("episode.html", episode_id=episode_id, url=url)

@app.route('/get-topics', methods=["POST"])
def get_topics():
    templ = """
    <ul>
    {% for topic in topics %}
        <li>{{ topic.text }}</li>
    {% endfor %}
    </ul>
    """
    url = request.form['url']
    episode_id = request.form['episode_id']
    print(url, episode_id)
    episode = read_db(episode_id)
    if episode and episode.conversation_id:
        conversation = symbl.Conversations.get_topics(conversation_id=episode.conversation_id, parameters={"sentiment": True})
        return render_template_string(templ, topics=conversation.topics, conversation_id=episode.conversation_id)
    r = requests.get(url)
    r_url = r.url
    request_body = {
            'url': r_url.strip(),
            'name': f'Request',
    }

    conversation_object = symbl.Audio.process_url(payload=request_body)
    save_conversation(episode_id, url, conversation=conversation_object, podcast=episode)

    cid=conversation_object.get_conversation_id()
    return render_template_string(templ, topics=conversation_object.get_topics().topics)

@app.route('/get-action-items', methods=["POST"])
def get_action_items():
    templ = """
    <ul>
    {% if actions %}
        {% for action in actions %}
            <li>{{ action }}</li>
        {% endfor %}
    {% else %}
        <li> No actions found</li>
    {% endif %}
    </ul>
    """
    url = request.form['url']
    episode_id = request.form['episode_id']
    episode = read_db(episode_id)
    print(episode.conversation_id)
    if episode and episode.conversation_id:
        conversation = symbl.Conversations.get_action_items(conversation_id=episode.conversation_id) 
        print(conversation)
        return render_template_string(templ, actions=conversation.action_items, conversation_id=episode.conversation_id)
    r = requests.get(url)
    r_url = r.url
    request_body = {
            'url': r_url.strip(),
            'name': f'Request',
    }

    conversation_object = symbl.Audio.process_url(payload=request_body)
    save_conversation(episode_id, url, conversation=conversation_object, podcast=episode)

    return render_template_string(templ, actions=conversation_object.get_action_items().action_items)

@app.route('/get-follow-ups', methods=["POST"])
def get_follow_ups():
    templ = """
    <ul>
    {% for follow_up in follow_ups %}
        <li>{{ follow_up.text }}</li>
    {% endfor %}
    </ul>
    """
    url = request.form['url']
    episode_id = request.form['episode_id']
    episode = read_db(episode_id)
    if episode and episode.conversation_id:
        conversation = symbl.Conversations.get_follow_ups(conversation_id=episode.conversation_id) 
        return render_template_string(templ, follow_ups=conversation.follow_ups, conversation_id=episode.conversation_id)
    r = requests.get(url)
    r_url = r.url
    request_body = {
            'url': r_url.strip(),
            'name': f'Request',
    }

    conversation_object = symbl.Audio.process_url(payload=request_body)
    save_conversation(episode_id, url, conversation=conversation_object, podcast=episode)

    return render_template_string(templ, follow_ups=conversation_object.get_follow_ups().follow_ups)

@app.route('/get-transciption', methods=['POST'])
def get_transcription():
    templ = """
    <p>
    {{ transciption }}
    </p>
    """
    url = request.form.get('url')
    episode_id = request.form.get('episode_id')
    episode = read_db(episode_id)
    if episode and episode.rev_job_id:
        job_details = client.get_job_details(episode.rev_job_id)
        transcript_text = "Still working on it"
        if job_details.status.name == "TRANSCRIBED":
            transcript_text = client.get_transcript_text(episode.rev_job_id)
        return render_template_string(templ, transciption=transcript_text)
    job = client.submit_job_url(url)
    save_conversation(episode_id, url, rev_job_id=job.id)
    status = job.status.name
    transcript_text = "Buffering"
    while True:
        if status == "IN_PROGRESS":
            time.sleep(5)
            continue
        elif status == "FAILED":
            transcript_text =  "Failed to transcribe podcast"
            break

        if status == "TRANSCRIBED":
            transcript_text = client.get_transcript_text(job.id)
            break

    return render_template_string(templ, transciption=transcript_text, podcast=episode)

# if __name__ == "__main__":
    # db.create_all()
    # app.run(debug=True)
