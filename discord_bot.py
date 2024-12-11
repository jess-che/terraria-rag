from interactions import Client, Intents, slash_command, listen, SlashContext, slash_option, OptionType
from dotenv import load_dotenv
import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import asyncio
from fuzzywuzzy import fuzz

# Load environment variables from .env file
load_dotenv()

# Set OpenAI API Key from .env
client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)


# Set the paths to the FAISS index and metadata files
local_folder = "index"  # Set this to the folder where you downloaded the files
index_file = os.path.join(local_folder, "terraria_index.faiss")
metadata_file = os.path.join(local_folder, "metadata.json")

# Initialize the bot with all intents
bot = Client(intents=Intents.ALL)

# Event listener for bot being ready
@listen()
async def on_ready():
    print("Bot is ready to receive messages!")

# Debugging event listener to see messages
@listen()
async def on_message_create(event):
    print(f"message received: {event.message.content}")
    

def retrieve(query, index_file, metadata_file, model, top_k=3, title_weight=1.5, section_weight=1.2):
    # Step 1: Remove stop words and encode the query
    stop_words = set(["how", "to", "with", "for", "the", "a", "an", "in", "at", "of"])
    query_tokens = [word for word in query.split() if word.lower() not in stop_words]
    cleaned_query = ' '.join(query_tokens)  # Reduced query, e.g., "craft workbench"
    query_embedding = model.encode([cleaned_query], convert_to_tensor=False)
    
    # Step 2: Load the FAISS index and search for closest matches
    index = faiss.read_index(index_file)
    distances, indices = index.search(np.array(query_embedding), k=top_k)
    
    # Step 3: Load metadata for each result
    with open(metadata_file, "r", encoding="utf-8") as meta_f:
        metadata = json.load(meta_f)
    
    results = []
    for i, distance in zip(indices[0], distances[0]):
        if 0 <= i < len(metadata):
            metadata_entry = metadata[i]
            text = metadata_entry.get("text", "[No text available]")
            page_title = metadata_entry.get("page_title", "").lower()
            section_title = metadata_entry.get("section_title", "").lower()
            
            # Step 4: Convert distance to similarity score (using exponential decay for better weighting)
            score = np.exp(-distance)  # Exponential decay favors closer distances more heavily
            
            # Step 5: Fuzzy matching for title and section title boosts
            if fuzz.partial_ratio(cleaned_query.lower(), page_title) > 80:
                score *= title_weight  # Boost score if query is similar to page title
            if fuzz.partial_ratio(cleaned_query.lower(), section_title) > 80:
                score *= section_weight  # Boost score if query is similar to section title
            
            # Step 6: Add weight to key tokens in the query
            important_terms = set(["craft", "build", "make", "recipe", "create"])
            for term in important_terms:
                if term in cleaned_query.lower():
                    score *= 1.2  # Boost the score for matching key tokens
                    
            results.append({
                "text": text,
                "metadata": metadata_entry,
                "score": score  # Add score to sort later
            })
    
    # Step 7: Sort the results by boosted score (higher is better)
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    
    # Step 8: Return the top_k results
    return results[:top_k]


def generate_response_gpt(query, retrieved_chunks, max_input_tokens=800, max_output_tokens=300):
    try:
        # Limit the size of retrieved chunks to avoid exceeding token limits
        truncated_chunks = retrieved_chunks[:max_input_tokens // 100]  # Assumes each chunk is approximately 100 tokens
        
        # Construct the prompt to be sent to the GPT model
        prompt = f"User Query: {query}\n\nRelevant Information:\n"
        for chunk in truncated_chunks:
            prompt += f"{chunk['text']}\n"
        prompt += "\nAnswer:"
        
        # Generate the response using the chat completion API
        stream = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides detailed and accurate responses."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo-1106",
            stream=True,
            max_tokens=max_output_tokens,  # Maximum tokens for the response
            temperature=0.7  # Controls randomness in responses
        )
        
        # Collect and print the streaming response
        response_content = ""
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            print(content, end="")  # Print the streaming content as it arrives
            response_content += content  # Collect the full response content
        
        return response_content  # Return the entire response
    
    except Exception as e:
        print(f"Error occurred for query: '{query}' - {e}")
        return "An error occurred while processing this query. Please try again."


def run_rag_system(query, index_file, metadata_file):
    """Retrieve and generate a response using the RAG system."""
    print(f"Processing query: {query}")
    bert_model = SentenceTransformer('all-MiniLM-L6-v2')
    retrieved_chunks = retrieve(query, index_file, metadata_file, bert_model)
    response = generate_response_gpt(query, retrieved_chunks)
    return response


# Asynchronous wrapper for the RAG system
async def async_run_rag_system(query: str) -> str:
    """Run RAG system asynchronously using an event loop."""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, run_rag_system, query, index_file, metadata_file)
    return response


# Query Command
@slash_command(name="query", description="Enter your query to search the Terraria RAG system")
@slash_option(
    name="input_text",
    description="Enter your query here",
    required=True,
    opt_type=OptionType.STRING,
)
async def get_response(ctx: SlashContext, input_text: str):
    """Handle the /query command to search the RAG system."""
    await ctx.defer()  # Acknowledge command to avoid timeout
    try:
        # Call the RAG system asynchronously
        response = await async_run_rag_system(input_text)
        response_message = f'**Input Query**: {input_text}\n\n**Response**: {response}'
    except Exception as e:
        response_message = f"An error occurred while processing your query. Please try again. \n\n**Error**: {e}"
    await ctx.send(response_message)
    
# Show Chunks Command
@slash_command(name="context", description="Show the retrieved chunks from the RAG system")
@slash_option(
    name="input_text",
    description="Enter your query here",
    required=True,
    opt_type=OptionType.STRING,
)
async def show_chunks(ctx: SlashContext, input_text: str):
    await ctx.defer()
    try:
        bert_model = SentenceTransformer('all-MiniLM-L6-v2')
        retrieved_chunks = retrieve(input_text, index_file, metadata_file, bert_model)
        
        all_chunk_data = ""
        
        for chunk in retrieved_chunks:
            # Collect all the information from the chunk, not just the text
            chunk_info = ""
            for key, value in chunk.items():
                chunk_info += f"**{key.capitalize()}**: {value}\n\n"
            all_chunk_data += chunk_info + "\n\n"
        
        # Split the collected chunk data into parts of 1800 characters each to avoid exceeding the 2000 character limit
        chunk_size = 1800  # Ensure that each message part is under the 2000 character Discord limit
        parts = [all_chunk_data[i:i + chunk_size] for i in range(0, len(all_chunk_data), chunk_size)]
        
        for i, part in enumerate(parts):
            response_message = f'**Chunk Part {i + 1}/{len(parts)}**\n\n{part}'
            await ctx.send(response_message)
    except Exception as e:
        response_message = f"An error occurred while processing your query. Please try again. \n\n**Error**: {e}"
        await ctx.send(response_message)




# Start the bot using the Discord token from .env
bot.start(os.getenv("DISCORD_TOKEN"))


