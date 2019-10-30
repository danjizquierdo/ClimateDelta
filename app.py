from flask import Flask, request, render_template

from summary_functions import get_articles

app = Flask(__name__)
app.config['DEBUG'] = True

@app.route('/', methods = ['GET'])
def render_page():
    return render_template('index.html')

@app.route('/', methods = ['POST'])
def render_article():
    query = request.form.get('query')
    amt = request.form.get('amt')
    summary = get_articles(query,amt)
    return render_template('results.html', summary=summary, query=query)

if __name__ == '__main__':
    app.run()
