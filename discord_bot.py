from interactions import Client, Intents, slash_command, listen, SlashContext, slash_option, OptionType
from dotenv import load_dotenv
import os

# get environment variable
load_dotenv()

# Initialize the bot with all intents
bot = Client(intents=Intents.ALL)

# event listener for bot being ready
@listen()
async def on_ready():
    print("Bot is ready to receive messages!")

# debugging event listener to see messages
@listen()
async def on_message_create(event):
    print(f"message received: {event.message.content}")
    
# command for quert
@slash_command(name="query", description="Enter your query :)")
@slash_option(
    name="input_text",
    description="input text",
    required=True,
    opt_type=OptionType.STRING,
)
async def get_response(ctx: SlashContext, input_text: str):
    await ctx.defer()
    # response = await data_querying(input_text)
    response = 'test response'
    response = f'**Input Query**: {input_text}\n\n{response}'
    await ctx.send(response)
    
# start the bot using the discord token
bot.start(os.getenv("DISCORD_TOKEN"))
