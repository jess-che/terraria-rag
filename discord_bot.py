from interactions import Client, Intents, slash_command, listen, SlashContext, slash_option, OptionType, Role
from dotenv import load_dotenv
import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import asyncio
from fuzzywuzzy import fuzz

AUTHORIZED_ROLE_IDS = [1316917479838322718] 

load_dotenv()

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

# path to files from index
local_folder = "index"  
index_file = os.path.join(local_folder, "terraria_index.faiss")
metadata_file = os.path.join(local_folder, "metadata.json")

bot = Client(intents=Intents.ALL)
# initaize bot
@listen()
async def on_ready():
    print("Bot is ready to receive messages!")

# this is just to read normal messages to see if it works
@listen()
async def on_message_create(event):
    print(f"message received: {event.message.content}")
    

def retrieve(query, index_file, metadata_file, model, top_k=3, title_weight=1.5, section_weight=1.2):
    # Step 1: remove small words and encode the query
    stop_words = set(["how", "to", "with", "for", "the", "a", "an", "in", "at", "of"])
    query_tokens = [word for word in query.split() if word.lower() not in stop_words]
    cleaned_query = ' '.join(query_tokens)  # Reduced query, e.g., "craft workbench"
    query_embedding = model.encode([cleaned_query], convert_to_tensor=False)
    
    # Step 2: load the FAISS index and search for closest matches
    index = faiss.read_index(index_file)
    distances, indices = index.search(np.array(query_embedding), k=top_k)
    
    # Step 3: load metadata for each result
    with open(metadata_file, "r", encoding="utf-8") as meta_f:
        metadata = json.load(meta_f)
    
    # fine tune the distance match
    results = []
    for i, distance in zip(indices[0], distances[0]):
        if 0 <= i < len(metadata):
            metadata_entry = metadata[i]
            text = metadata_entry.get("text", "[No text available]")
            page_title = metadata_entry.get("page_title", "").lower()
            section_title = metadata_entry.get("section_title", "").lower()
            
            # Step 4: using exponential decay, convert distance to score from the fais distances
            score = np.exp(-distance)  
            
            # Step 5: matching for title and section title 
            if fuzz.partial_ratio(cleaned_query.lower(), page_title) > 80:
                score *= title_weight  
            if fuzz.partial_ratio(cleaned_query.lower(), section_title) > 80:
                score *= section_weight  
             
            results.append({
                "text": text,
                "metadata": metadata_entry,
                "score": score  
            })
    
    # Step 7: sort the results by score (higher is better)
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    
    # Step 8: return the top_k results
    return results[:top_k]


def generate_response_gpt(query, retrieved_chunks, max_input_tokens=800, max_output_tokens=300, temperature=0.7):
    try:
        # Step 1: for the chunks, limit them to 200 tokens
        estimated_chunk_token_size = 200  
        max_chunks = max_input_tokens // estimated_chunk_token_size
        truncated_chunks = retrieved_chunks[:max_chunks]  #

        # Step 2: initial prompt with user query
        prompt = (
            f"User Query: {query}\n\n"
            f"You are a Terraria Q&A bot with deep knowledge of the game. You provide clear, concise, and accurate answers to Terraria-related questions.\n"
            f"Use the following relevant information to form your response.\n"
            f"Provide step-by-step concise instructions, specific item names, and game-related terminology when relevant.\n"
            f"If multiple approaches exist, mention them.\n"
            f"If you do not know the answer, clearly and politely state that you do not have the information, but offer suggestions on where the user might look (like the Terraria Wiki, forums, or other community resources).\n\n"
            f"--- Retrieved Context ---\n"
        )
        
        # Step 3: add in the context
        for i, chunk in enumerate(truncated_chunks):
            prompt += f"({i+1}) {chunk['text']}\n"
        
        prompt += "\n--- End of Context ---\n\n"
        prompt += "Answer the user's question in a clear, step-by-step manner, citing any relevant context when appropriate.\nAnswer:"

        # Step 4: now using the chatgpt feature double sandwich the prompt to get paying attention to context both in here and in the prompt
        stream = client.chat.completions.create(
            messages=[
                {"role": "system", "content": (
                    "You are a Terraria Q&A assistant with expertise on game mechanics, bosses, items, and progression. "
                    "If you do not know the answer to a question, politely inform the user that you don't have the exact information, "
                    "but suggest helpful resources such as the Terraria Wiki, forums, or other community resources."
                )},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo-1106",
            stream=True,
            max_tokens=max_output_tokens,
            temperature=temperature
        )

        # Step 5: stream content to discord
        response_content = ""
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            print(content, end="")  
            response_content += content  

        return response_content 
    
    except Exception as e:
        error_message = f"Error occurred for query: '{query}' - {e}"
        print(error_message)
        return "An error occurred while processing this query. Please try again later."

# this is the rag system of retrieval and generation
def run_rag_system(query, index_file, metadata_file):
    print(f"Processing query: {query}")
    bert_model = SentenceTransformer('all-MiniLM-L6-v2')
    retrieved_chunks = retrieve(query, index_file, metadata_file, bert_model)
    response = generate_response_gpt(query, retrieved_chunks)
    return response


# call rag asyncrenously
async def async_run_rag_system(query: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, run_rag_system, query, index_file, metadata_file)
    return response

@slash_command(name="query", description="Enter your query to search the Terraria RAG system")
@slash_option(
    name="input_text",
    description="Enter your query here",
    required=True,
    opt_type=OptionType.STRING,
)
async def get_response(ctx: SlashContext, input_text: str):
    await ctx.defer()  
    try:
        response = await async_run_rag_system(input_text)
        response_message = f'**Input Query**: {input_text}\n\n**Response**: {response}'
    except Exception as e:
        response_message = f"An error occurred while processing your query. Please try again. \n\n**Error**: {e}"
    await ctx.send(response_message)
    
# context command to help with debugging
@slash_command(name="context", description="Show the retrieved chunks from the RAG system")
@slash_option(
    name="input_text",
    description="Enter your query here",
    required=True,
    opt_type=OptionType.STRING,
)
async def show_chunks(ctx: SlashContext, input_text: str):
    # Check if the user has any of the allowed roles
    user_roles = [role.id for role in ctx.author.roles]
    if not any(role_id in user_roles for role_id in AUTHORIZED_ROLE_IDS):
        await ctx.send("❌ You do not have permission to use this command.", ephemeral=True)
        return

    await ctx.defer()  
    try:
        bert_model = SentenceTransformer('all-MiniLM-L6-v2')
        retrieved_chunks = retrieve(input_text, index_file, metadata_file, bert_model)
        
        all_chunk_data = ""
        
        for chunk in retrieved_chunks:
            chunk_info = ""
            for key, value in chunk.items():
                chunk_info += f"**{key.capitalize()}**: {value}\n\n"
            all_chunk_data += chunk_info + "\n\n"
        
        # discord has a 2000 character limit so split to make sure under
        chunk_size = 1800  
        parts = [all_chunk_data[i:i + chunk_size] for i in range(0, len(all_chunk_data), chunk_size)]
        
        for i, part in enumerate(parts):
            response_message = f'**Chunk Part {i + 1}/{len(parts)}**\n\n{part}'
            await ctx.send(response_message)
    except Exception as e:
        response_message = f"An error occurred while processing your query. Please try again. \n\n**Error**: {e}"
        await ctx.send(response_message)

bot.start(os.getenv("DISCORD_TOKEN"))


