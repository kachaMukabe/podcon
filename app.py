from flask import abort, Flask, jsonify, request, render_template, render_template_string
from flask_sqlalchemy import SQLAlchemy
from os import environ

import symbl
import podcastindex
import pprint
import requests


config = {
        "api_key": environ.get("API_KEY"),
        "api_secret": environ.get("API_SECRET") 
}


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)


class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    episode_id = db.Column(db.Integer)
    conversation_id = db.Column(db.String(40))
    episode_url = db.Column(db.String(120))

    def __init__(self, episode_id, conversation_id, episode_url):
        self.episode_id = episode_id
        self.conversation_id = conversation_id
        self.episode_url = episode_url

    def __repr__(self):
        return f"Podcast {self.episode_id}"

def read_db(episode_id):
    episode = Podcast.query.filter_by(episode_id=episode_id).first()
    return episode

def save_conversation(conversation, episode_id, url):
    podcast = Podcast(episode_id, conversation.get_conversation_id(), url)
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
    print(result['feeds'])
    templ = """
    {% for pod in podcasts %}
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
            <a class="card-footer-item" hx-indicator="#search-indicator" hx-get="/episodes/{{pod.id}}" hx-target="#episodes-div">Get episodes</a>
        </footer>
    </div>
    {% endfor %}
    """
    podcasts = result['feeds']
    return render_template_string(templ, podcasts=podcasts)
    # return jsonify(result['feeds']), 200

@app.route('/episodes/<id>')
def episodes(id):
    print(id)
    index = podcastindex.init(config)
    result = index.episodesByFeedId(id)
    pprint.pprint(result['items'][0])
    url = result['items'][0]['enclosureUrl']
    templ = """
    {% for episode in episodes %}
    <div class="card block">
        <div class="card-content">
            <div class="media">
                <div class="media-content">
                    <p class="title is-4">{{ episode.title }}</p>
                </div>
            </div>
        </div>
        <footer class="card-footer">
            <form hx-target="#final-div" hx-post="/analyze" hx-indicator="#final-indicator" class="card-footer-item">
            <input hidden name="url" value="{{episode.enclosureUrl}}">
            <input hidden name="episode_id" value="{{episode.id}}">
            <input type="submit" value="Analyze" class="button is-white">
            </form>
        </footer>
    </div>
    {% endfor %}
    """
    episodes = result['items']
    return render_template_string(templ, episodes=episodes)

@app.route('/analyze', methods=['POST'])
def analyze():
    templ = """
    <div class="card block">
        <header class="card-header">
            <p class="card-header-title">
              Podcast analysis
            </p>
        </header>
        <div class="card-content">
            <div class="content">
            {% for topic in topics %}
            <span class="tag">{{ topic.text }}</span>
            {% endfor %}
            </div>
        </div>
        <footer class="card-footer">
            <a href="/analysis?cid={{ conversation_id }}" class="card-footer-item">Go to full Analysis</a>
        </footer>
    </div>
    """
    url = request.form['url']
    episode_id = request.form['episode_id']
    episode = read_db(episode_id)
    if episode:
        print(episode)
        conversation = symbl.Conversations.get_topics(conversation_id=episode.conversation_id, parameters={"sentiment": True})
        return render_template_string(templ, topics=conversation.topics, conversation_id=episode.conversation_id)
    r = requests.get(url)
    r_url = r.url
    print(r_url)
    request_body = {
            'url': r_url.strip(),
            'name': f'Request',
    }

    conversation_object = symbl.Audio.process_url(payload=request_body)
    topics = save_conversation(conversation_object, episode_id, url)

    print(conversation_object.get_topics())
    cid=conversation_object.get_conversation_id()
    return render_template_string(templ, topics=topics, conversation_id=cid)

@app.route('/analysis', methods=['GET'])
def analysis():
    conversation_id = request.args.get('cid')
    topics = symbl.Conversations.get_topics(conversation_id=conversation_id, parameters={"sentiment": True})
    follow_ups = symbl.Conversations.get_follow_ups(conversation_id=conversation_id)
    questions = symbl.Conversations.get_questions(conversation_id=conversation_id)
    action_items = symbl.Conversations.get_action_items(conversation_id=conversation_id)
    return render_template("analysis.html", topics=topics.topics, follow_ups=follow_ups.follow_ups, questions=questions.questions, action_items=action_items.action_items)


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
