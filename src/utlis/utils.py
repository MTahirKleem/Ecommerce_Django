from django.db.models import Count
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import random
from app.models import Product, UserInteraction

def get_recommendations(user_id, query, k=100):
    # Get products based on the search query
    search_products = Product.objects.filter(product_name__icontains=query)
    # If there are search products, select a random sample; otherwise, select random products
    if search_products.exists():
        # TF-IDF vectorization for product_name features
        tfidf_vectorizer = TfidfVectorizer()
        tfidf_matrix = tfidf_vectorizer.fit_transform(search_products.values_list('product_name', flat=True))

        # Train k-NN model using the TF-IDF matrix
        knn_model = NearestNeighbors(n_neighbors=k, metric='cosine')
        knn_model.fit(tfidf_matrix)

        # Find k nearest neighbors among the search products
        _, indices = knn_model.kneighbors(tfidf_matrix)
        recommended_product_ids = [search_products[int(idx)].id for idx in indices[0]]
    else:
        recommended_product_ids = random.sample(list(Product.objects.all().values_list('id', flat=True)), k)

    return list(recommended_product_ids)




