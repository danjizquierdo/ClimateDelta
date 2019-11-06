import requests
from bs4 import BeautifulSoup as bs
import re
import nltk
import heapq
import logging

# # Necessary downloads
nltk.download('punkt')
nltk.download('stopwords')
logger = logging.getLogger('requester')
m_logger = logging.getLogger('modeler')
logger.setLevel(logging.DEBUG)
m_logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('articles.log')
m_fh = logging.FileHandler('summaries.log')
fh.setLevel(logging.DEBUG)
m_fh.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt='%(asctime)s;%(message)s-', datefmt='%m-%d-%Y %H:%M:%S')
m_formatter = logging.Formatter(
    fmt='%(asctime)s;Query:%(message)s \n %(headline)s: \n%(joined_sentences)s \n\nSummary\n\n %(summary)s',
    datefmt='%m-%d-%Y %H:%M:%S')
fh.setFormatter(formatter)
m_fh.setFormatter(m_formatter)
logger.addHandler(fh)
m_logger.addHandler(m_fh)

# Article requests which prints headline, authors, publish date and the summary
def get_articles(query, amt):
    amt = int(amt)
    soup = bs(requests.get('https://www.scirp.org/journal/Articles.aspx?searchCode='+re.sub('\s','+',query)+
                           '&searchField=All&page=1&SKID=58821535').text,'html.parser')

    # Loop through results until the desired amount are retrieved
    summaries = []
    flag = 0
    for count, result in enumerate(soup.find_all('div', class_='reviewpaper')):
        article = {}
        if count<amt:
            for p in result.find_next_siblings():
                # Find the full_html link
                if p.span:
                    article['href'] = p.span.a.get('href')[2:]
                    break
                else:
                    continue
            # Find all of the authors, also grabs a link to their other articles
            authors = result.find_next_sibling().find_next_sibling().find_all('a')
            cite = {}
            # Create author dictionaries
            for author in authors:
                cite[author.text] = 'https://www.scirp.org/journal/'+author.get('href')
            article['authors'] = cite
        else:
            break
        #
        try:
            summary = summarize(article, query)
            if summary:
                summaries.append(summary)
            else:
                flag = 1
                amt+=1
        except Exception as e:
            logger.error(f'Error {e} on {article["href"]}')
            amt += 1
            flag = 1

    logger.debug(f'Query: {query} \n Article summaries created: {summaries}')
    if len(summaries):
        flag = 0
        return summaries, flag
    else:
        return 'Dog-gone it, I messed it up', flag


# Summarization pipeline which takes in a single url
def summarize(article_dict, query):
    response = {}
    response['authors'] = article_dict['authors']
    response['url'] = 'https://'+article_dict['href']
    # Request given article
    article = bs(requests.get(response['url']).text, 'html.parser')

    # Get a list of all sentences in the article
    response['date'] = article.find(class_='cs_time').text
    sentences = []
    for paragraph in article.find(class_='E-Title1').find_next_siblings('p', attrs={'style': None}):
        if paragraph.text == 'Acknowledgements':
            break
        elif paragraph.get('class'):
            pass
        else:
            formatted_text = re.sub(r'\s+', ' ', str(paragraph.text))
            formatted_text = re.sub(r'\[[0-9]+\]', '', formatted_text)
            formatted_text = re.sub(r' \.', '.', formatted_text)
            formatted_text = re.sub(r' , ', ' ', formatted_text)
            sentences.append(formatted_text.strip())
    response['headline'] = article.find(class_='cs_t1').text

    # Take just the text of the article and join it
    response['joined_sentences'] = ' '.join(sentences)

    # Preprocess full text
    formatted_text = re.sub('[^a-zA-Z]', ' ', response['joined_sentences'])
    formatted_text = re.sub(r'\s+', ' ', formatted_text)

    # Retokenize processed sentences and load standard stopwords
    sentence_list = nltk.sent_tokenize(response['joined_sentences'])
    stopwords = nltk.corpus.stopwords.words('english')
    stopwords.extend('Figure')

    # Determine word frequencies for full article
    word_frequencies = {}
    for word in nltk.word_tokenize(formatted_text):
        if word not in stopwords:
            if word not in word_frequencies.keys():
                    word_frequencies[word.lower()] = 1
            else:
                if word in query:
                    word_frequencies[word.lower()] += 3
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
    m_logger.debug(f'{query}', extra=response)
    return response


# def summarize(article,query):
#     response = produce_summary(article['href'],query)
#
#     return '\n'.join(
#         [response['headline'],
#          'by ' + ', '.join([', '.join(list(article['authors'].keys())), response['date']]),
#          re.sub(r'\n', ' ', response['summary']).strip()]) + '\n\n'
