# install dependencies
# !pip install faiss-cpu sentence-transformers transformers

# import dependencies
from google.colab import drive
import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from transformers import GPT2LMHeadModel, GPT2Tokenizer, AutoTokenizer, AutoModelForCausalLM

# connect to drive
print("Mounting Google Drive...")
drive.mount('/content/drive')

drive_folder = "/content/drive/MyDrive/Terraria_RAG"
os.makedirs(drive_folder, exist_ok=True)  

preprocessed_file = "/content/drive/MyDrive/Terraria_RAG/terraria_preprocessed.json"
index_file = "/content/drive/MyDrive/Terraria_RAG/terraria_index.faiss"
metadata_file = "/content/drive/MyDrive/Terraria_RAG/metadata.json"

# index the data with FAISS
def index_data(preprocessed_file, index_file, metadata_file):
    model = SentenceTransformer('all-MiniLM-L6-v2')     # bert like model to encode data

    # read the processed file
    with open(preprocessed_file, "r", encoding="utf-8") as f:
        data_chunks = json.load(f)
        # print(f"Loaded {len(data_chunks)} chunks from {preprocessed_file}.")

    # save the text to embed, and it to the metadata so can be indexed 
    texts = [chunk["text"] for chunk in data_chunks]
    metadata = [
        {"text": chunk["text"], "page_title": chunk["metadata"]["page_title"], "section_title": chunk["metadata"]["section_title"]}
        for chunk in data_chunks
    ]
    
    # convert to embeddings using bert model
    # print("Encoding text chunks into embeddings...")
    embeddings = model.encode(texts, convert_to_tensor=False)
    # print(f"Generated {len(embeddings)} embeddings.")

    # create the FAISS index (the data base and store it)
    # print("Creating FAISS index...")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    faiss.write_index(index, index_file)
    # print(f"FAISS index saved to {index_file}.")

    # save the mdetadata
    # print("Saving metadata...")
    with open(metadata_file, "w", encoding="utf-8") as meta_f:
        json.dump(metadata, meta_f, indent=4)
    # print(f"Metadata saved to {metadata_file}.")