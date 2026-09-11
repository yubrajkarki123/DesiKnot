from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from DesiKnot_App.models import Product

def get_similar_products(product_id, top_n=4):

    products = list(Product.objects.all())

    if not products:
        return []

    product_ids = [p.id for p in products]

    texts = [
        (p.name or "") + " " + (p.description or "")
        for p in products
    ]

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(texts)

    similarity_matrix = cosine_similarity(tfidf_matrix)

    if product_id not in product_ids:
        return []

    index = product_ids.index(product_id)

    scores = list(enumerate(similarity_matrix[index]))

    scores = sorted(scores, key=lambda x: x[1], reverse=True)

    recommended = []

    for i in scores[1:top_n+1]:
        recommended.append(products[i[0]])

    return recommended