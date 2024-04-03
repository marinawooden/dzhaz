from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
import requests
import os
import json
import uuid
from dotenv import load_dotenv
import chromadb
import asyncio
import pinecone
import csv
import time
from langchain.document_loaders.csv_loader import CSVLoader
import discogs_client
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import soundfile as sf
import openl3

# chroma_client = chromadb.PersistentClient(path="../data/db")

load_dotenv()

LASTFM_KEY = os.getenv('LASTFM_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Replace with your api key
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_API_ENV ="gcp-starter"

DISCOGS_USER_TOKEN = os.getenv('DISCOGS_USER_TOKEN')
DISCOGS_APPLICATION = os.getenv('DISCOGS_APPLICATION')
DISCOGS_USER_SECRET = os.getenv('DISCOGS_USER_SECRET')

SPOTIFY_CLIENT = os.getenv('SPOTIFY_CLIENT')
SPOTIFY_SECRET = os.getenv('SPOTIFY_SECRET')

# discogs client
discogs = discogs_client.Client(
  "Marina/1.0",
  user_token="JRRJFhHSLBoxUKMmwGRgrHaMHpnogZkNpgRmXPaF"
)


url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=oubliette99&api_key={LASTFM_KEY}&format=json"

num_pages = 1


async def main():
  try:
    song_arr = await get_tracks()
    # store_as_vector()
  except Exception as e:
    print(f"Error: {e}")
  
def store_as_vector():
  # initialize pinecone
  pinecone.init(
    api_key=PINECONE_API_KEY,
    environment=PINECONE_API_ENV
  )

  # read music data
  loader = CSVLoader(file_path='../data/music.csv')
  song_data = loader.load()

  # embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
  # index_name="dzhaz-bot"

  # Pinecone.from_documents(song_data, embeddings, index_name=index_name)
  # print("Successfully uploaded to Pinecone")


async def get_tracks():
  # get intial recent songs
  all_songs = requests.get(url)
  status_check(all_songs)
  all_songs = all_songs.json()

  # get spotify token
  client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT, client_secret=SPOTIFY_SECRET)
  sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

  results = []
  total_pages = all_songs["recenttracks"]["@attr"]['totalPages']
  total_songs = all_songs["recenttracks"]["@attr"]["total"]


  f = open("../data/total_listens.txt", "r")
  # get the previous # of total listens
  prev_total_songs = int(f.readline())
  f.close()

  total_songs = 200 # TODO: remove later, defined on line 83
  prev_total_songs = 0 # TODO: remove later, defined on line 88
  # how many new songs to add to db
  add_count = int(total_songs) - prev_total_songs
  
  # traverse by 200
  # print(add_count)

  page = 1

  # # UNCOMMENT WHEN YOU NEED MORE THAN 200 SONGS
  # while add_count >= 200:
  #   results_per_page = requests.get(url + "&page=" + str(page) + "&limit=200")
  #   status_check(results_per_page)
  #   results_per_page = results_per_page.json()
  #   results_per_page = results_per_page["recenttracks"]["track"]

  #   add_count -= 200
  #   page += 1

  #   results += results_per_page

  # get the remaining songs
  results_per_page = requests.get(url + "&page=" + str(page) + "&limit=200")
  status_check(results_per_page)
  results_per_page = results_per_page.json()
  results += results_per_page["recenttracks"]["track"][0:add_count]

  # print(f"All songs: {len(results)}")
  filtered_songs = filter_songs(results)

  formatted_songs = []
  seen = set()

  with open('../data/test.csv', 'w', newline='\n') as testdb:
    spamwriter = csv.writer(testdb, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(["title", "artist_name", "artist_uri", "genres", "image", "last_fm_uri", "spotify_uri", "preview_url", "id"])

    # TODO: Uncomment to get to work
    # for song in results:
    for i in range(1):
      song = results[i]

      try:
        artist = song["artist"]["#text"]
        title = song["name"]

        song_info_url = f"http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={LASTFM_KEY}&artist={artist}&track={title}&format=json"
        song_info = requests.get(song_info_url)

        status_check(song_info)
        song_info = song_info.json()

        if "track" in song_info.keys():
          song_info = song_info["track"]
          extra_meta = sp.search(q=f'{song_info["artist"]["name"]} - {song_info["name"]}', type='track', limit=1)

          # print( and extra_meta.total)
          if "total" in extra_meta.keys() and extra_meta.total == 0:
            # omit if no results
            continue
    
          extra_meta = extra_meta["tracks"]["items"][0]
          unique_id = extra_meta['id']

          formatted_song = {
            "title": song_info["name"],
            "artist_name": song_info["artist"]["name"],
            "artist_uri": song_info["artist"]["url"],
            "genres": ', '.join([tag["name"] for tag in song_info["toptags"]["tag"]]),
            "image": song_info["image"][-1]["#text"] if "image" in song_info else "",
            "last_fm_uri": song_info["url"],
            "spotify_uri": extra_meta['external_urls']['spotify'],
            "preview_url": extra_meta['preview_url'],
            "id": unique_id
          }

          if unique_id not in seen:
            formatted_songs.append(formatted_song)
            spamwriter.writerow(formatted_song.values())

            audio, sr = sf.read(extra_meta['preview_url'])
            emb = openl3.get_audio_embedding(audio, sr)

            print(emb)
            
            seen.add(unique_id)
            print(f"Added {title}, {artist}")

          time.sleep(0.5)
        else:
          continue
      except Exception as e:
        continue

def filter_songs(songs):
  seen = set()
  ans = []

  for song in songs:
    unique_id = song["artist"]["name"] + song["name"] if "mbid" not in song.keys() else song["mbid"]
    
    if unique_id not in seen:
      ans.append(song)
      seen.add(unique_id)
  
  return ans

def status_check(req):
  if req.status_code != 200:
    raise Exception(req.text)
  return req
  


if __name__ == "__main__":
  loop = asyncio.get_event_loop()
  # loop.run_until_complete(main())
  # loop.run_until_complete(get_tracks())
  store_as_vector()