import requests
from bs4 import BeautifulSoup as bs
import re
import nltk
import heapq

# Necessary downloads
nltk.download('punkt')
nltk.download('stopwords')

def get_articles(query, amt=0):
    soup = bs(requests.get('https://www.sciencenews.org/?s='+re.sub('/s','+',query)+
                           '&topic=&start-date=&end-date=&orderby=date').text,'html.parser')
    articles = {}
    for count, h in enumerate(soup.find_all('h3')):
        if not amt or count-1<amt:
            a = h.find('a')
            if a:
                articles[a.get('href')]=a.text.strip()
    summarize(articles) if amt else summarize(articles)


# Summarization pipeline which takes in a single url
def produce_summary(url):
    # Request given article
    article = bs(requests.get(url).text, 'html.parser')

    # Get a list of all sentences in the article
    sentences = [p.text for p in article.find('article').find_all('p')]

    # Find just the date
    for count, sentence in enumerate(sentences):
        if re.search(r'.* (am|pm)', sentence) or re.search(r'\d.*ago', sentence):
            date = sentence
            break

    # Find the likely end of the article
    idx = [idx for idx, sentence in enumerate(sentences) if re.search('Questions or comments?', sentence)][0]

    # Take just the text of the article and join it
    sents = sentences[count + 1:idx]
    text = [re.sub(r'Updated .* (am|pm)', '', re.sub(r'.*[A-Z]{2,}\s\—', '', sent)) for sent in sents]
    joined_sentences = ' '.join(text)

    # Preprocess full text
    joined_sentences = re.sub(r'\(SN: [\s\d\,\.p/]+\)', ' ', joined_sentences)
    formatted_text = re.sub(r'\s+', ' ', joined_sentences)
    formatted_text = re.sub('[^a-zA-Z]', ' ', formatted_text)
    formatted_text = re.sub(r'\s+', ' ', formatted_text)

    # Retokenize processed sentences and load standard stopwords
    sentence_list = nltk.sent_tokenize(joined_sentences)
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
    summary = ' '.join(summary_sentences)
    return date, summary

def summarize(articles):
    for url,headline in articles.items():
        date, summary = produce_summary(url)

        print('\n'.join([headline,date,re.sub(r'\n',' ',summary).strip()])+'\n\n')