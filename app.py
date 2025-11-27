import streamlit as st
import pickle
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import os

# ---------- Configuration ----------
TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"   # your key (keep secret in prod)
TMDB_BASE = "https://image.tmdb.org/t/p/w500"      # cdn for posters
LOCAL_PLACEHOLDER = "placeholder.png"              # put this file next to this script
REQUEST_TIMEOUT = 6

# ---------- Helper to fetch poster as PIL Image with fallback ----------
def fetch_poster_image(movie_id):
    if not os.path.exists(LOCAL_PLACEHOLDER):
        return Image.open(LOCAL_PLACEHOLDER)

    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()

        data = resp.json()
        poster_path = data.get("poster_path")

        if poster_path:
            poster_url = "https://image.tmdb.org/t/p/w500" + poster_path
            try:
                img_data = requests.get(poster_url, timeout=6)
                img_data.raise_for_status()
                return Image.open(BytesIO(img_data.content))
            except:
                return Image.open(LOCAL_PLACEHOLDER)
        else:
            return Image.open(LOCAL_PLACEHOLDER)

    except:
        return Image.open(LOCAL_PLACEHOLDER)


# ---------- Load data (single load, adjust filenames to match your project) ----------
# Use whichever pickle contains the DataFrame you expect. Here I try to load 'movies_dict.pkl' first.
try:
    movies_dict = pickle.load(open('movies_dict.pkl','rb'))
    movies = pd.DataFrame(movies_dict)
except Exception:
    # fallback to old movies.pkl if present
    movies_list = pickle.load(open('movies.pkl', 'rb'))
    movies = pd.DataFrame(movies_list)

# similarity expected to be a square matrix saved as pickle
similarity = pickle.load(open('similarity.pkl','rb'))

# Confirm which column holds the external movie id (tmdb id) — try common names
if 'movie_id' in movies.columns:
    id_col = 'movie_id'
elif 'id' in movies.columns:
    id_col = 'id'
else:
    # print columns to help debug
    st.write("Movie DataFrame columns:", movies.columns.tolist())
    # try first numeric-like column
    numeric_cols = movies.select_dtypes(include=['int','float']).columns.tolist()
    id_col = numeric_cols[0] if numeric_cols else movies.columns[0]

# ---------- Recommendation function ----------
def recommend(movie_title):
    # get index of selected movie
    try:
        movie_index = movies[movies['title'] == movie_title].index[0]
    except Exception:
        st.error("Selected movie not found in DataFrame.")
        return [], []
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies = []
    recommend_movies_posters = []
    for i in movies_list:
        idx = i[0]
        # safe movie id extraction
        movie_id = movies.iloc[idx][id_col]
        recommended_movies.append(movies.iloc[idx]['title'])
        recommend_movies_posters.append(fetch_poster_image(movie_id))
    return recommended_movies, recommend_movies_posters

# ---------- Streamlit UI ----------
st.title("Pick A Movie For Me")

selected_movie_name = st.selectbox('Select the following movies', movies['title'].values)

if st.button('Recommend'):
    names, posters = recommend(selected_movie_name)
    if not names:
        st.write("No recommendations found.")
    else:
        cols = st.columns(5)
        for col, name, poster in zip(cols, names, posters):
            with col:
                st.text(name)
                # poster is a PIL.Image -> st.image will render it
                st.image(poster)
