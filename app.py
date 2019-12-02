from flask import Flask, request, render_template


from summary_functions import get_articles

app = Flask(__name__)
app.config['DEBUG'] = True

@app.route('/', methods = ['GET'])
def render_page():
    # Create endpoint for displaying homepage
    return render_template('index.html')

@app.route('/', methods = ['POST'])
def render_article():
    # Create endpoint for determining results based on posted info
    query = request.form.get('query')
    amt = request.form.get('amt')
    summary, flag = get_articles(query, amt)
    if not flag:
        return render_template('results.html', summaries=summary, query=query, amt=amt)
    elif flag:
        return render_template('no_results.html', summaries=summary)

@app.route('/about', methods =['GET'])
def render_about():
    # Setting up endpoint for eventual About page
    return render_template('about.html')

if __name__ == '__main__':
    app.run()
