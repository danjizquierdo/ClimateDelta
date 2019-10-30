import requests
from bs4 import BeautifulSoup as bs
import re
import nltk
import heapq
import logging

# # Necessary downloads
# nltk.download('punkt')
# nltk.download('stopwords')
logger = logging.getLogger('requester')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('articles.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt='%(asctime)s;%(message)s-', datefmt='%m-%d-%Y %H:%M:%S')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Article requests which prints headline, authors, publish date and the summary
def get_articles(query, amt):
    amt = int(amt)
    soup = bs(requests.get('https://www.scirp.org/journal/Articles.aspx?searchCode='+re.sub('\s','+',query)+
                           '&searchField=All&page=1&SKID=58821535').text,'html.parser')

    # Loop through results until the desired amount are retrieved
    summaries=''
    for count, result in enumerate(soup.find_all('div', class_='reviewpaper')):
        article = {}
        if count<amt:
            for p in result.find_next_siblings():
                # Find the full_html link
                if p.span:
                    article['href']=p.span.a.get('href')[2:]
                    break
                else:
                    continue
            # Find all of the authors, also grabs a link to their other articles
            authors = result.find_next_sibling().find_next_sibling().find_all('a')
            cite = {}
            # Create author dictionaries
            for author in authors:
                cite[author.text]=author.get('href')
            article['authors']=cite
        else:
            break
        #
        try:
            summaries += summarize(article)
        except ValueError as e:
            logger.debug(f'Error {e} on {article["href"]}')
            amt+=1
    logger.debug(f'Query: {query} \n Article summaries created: {summaries}')
    return summaries


# Summarization pipeline which takes in a single url
def produce_summary(url):
    response = {}

    # Request given article
    article = bs(requests.get('https://' + url).text, 'html.parser')

    # Get a list of all sentences in the article
    response['date'] = article.find(class_='cs_time').text
    sentences = []
    for paragraph in article.find(class_='E-Title1').find_next_siblings('p', attrs={'style': None}):
        if paragraph.text == 'Acknowledgements':
            break
        elif paragraph.get('class'):
            pass
        else:
            sentences.append(paragraph.text)
    response['headline'] = article.find(class_='cs_t1').text

    # Take just the text of the article and join it
    response['joined_sentences'] = ' '.join(sentences)

    # Preprocess full text
    formatted_text = re.sub(r'\s+', ' ', response['joined_sentences'])
    formatted_text = re.sub('[^a-zA-Z]', ' ', formatted_text)
    formatted_text = re.sub(r'\s+', ' ', formatted_text)

    # Retokenize processed sentences and load standard stopwords
    sentence_list = nltk.sent_tokenize(response['joined_sentences'])
    stopwords = nltk.corpus.stopwords.words('english')

    # Determine word frequencies for full article
    word_frequencies = {}
    for word in nltk.word_tokenize(formatted_text):
        if word not in stopwords:
            if word not in word_frequencies.keys():
                word_frequencies[word.lower()] = 1
            else:
                word_frequencies[word.lower()] += 1
    maximum_frequncy = max(word_frequencies.values())

    # Scale frequencies to most common non-stop word
    for word in word_frequencies.keys():
        word_frequencies[word] = (word_frequencies[word] / maximum_frequncy)

    # Get a score for each sentence based on the word frequencies that comprise it
    sentence_scores = {}
    for sent in sentence_list:
        for word in nltk.word_tokenize(sent.lower()):
            if word in word_frequencies.keys():
                if len(sent.split(' ')) < 30:
                    if sent not in sentence_scores.keys():
                        sentence_scores[sent] = word_frequencies[word]
                    else:
                        sentence_scores[sent] += word_frequencies[word]
    # Return sqrt(n) highest scoring sentences in descending order of weight
    summary_sentences = heapq.nlargest(int(len(sentence_list) ** (1 / 2)), sentence_scores, key=sentence_scores.get)
    summary_sentences.sort(key=sentence_list.index)
    response['summary'] = ' '.join(summary_sentences)
    return response


def summarize(article):
    response = produce_summary(article['href'])

    return '\n'.join(
        [response['headline'],
         'by ' + ', '.join([', '.join(list(article['authors'].keys())), response['date']]),
         re.sub(r'\n', ' ', response['summary']).strip()]) + '\n\n'
