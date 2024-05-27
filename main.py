import discord
import requests
from discord.ext import commands
import openai
import base64
import openai_integration
import aiohttp

DISCORD_TOKEN = openai_integration.DS_TOKEN

OPENAI_API_KEY = openai_integration.OI_API_KEY

openai.api_key = OPENAI_API_KEY
# Ініціалізація бота з заданим префіксом команд та налаштуваннями інтентів
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


# Глобальна змінна для зберігання вибору мови
language = "uk"  # За замовчуванням українська


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='generate', help='Generates an image from a prompt.')
async def generate(ctx, *, prompt: str):
    try:
        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
        image_url = response['data'][0]['url']
        await ctx.send(image_url)
    except Exception as e:
        await ctx.send('Sorry, an error occurred while generating the image.')
        print(e)


@bot.command(name='analyze',
             help='Analyzes an uploaded image with given parameters and provides options for numerical or regular list of keywords.')
async def analyze(ctx, subject_length: int, description_length: int, num_keywords: int,
                  numbered_keywords: bool = False):
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        image_bytes = await attachment.read()  # Reading the attachment as bytes

        # Convert image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        # Вибір тексту запиту залежно від мови
        if language == "uk":
            prompt_text = f"Згенеруй креативну назву довжиною не більше {subject_length} символів, опис довжиною приблизно {description_length} символів, і список {num_keywords} ключових слів розділених комою - українською мовою."
        else:
            prompt_text = f"Generate a creative title not longer than {subject_length} characters, description up to {description_length} characters, and a list of {num_keywords} keywords separated by comas - in english."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }

        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "max_tokens": description_length + num_keywords * 10
        }

        # Use aiohttp to make the asynchronous API call
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers,
                                    json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    message_content = result['choices'][0]['message']['content']
                    lines = message_content.split('\n')
                    modified_content = []

                    # Iterate over lines to find the keywords line and process it
                    for line in lines:
                        if line.startswith("Ключові слова:") or line.startswith("Keywords:"):
                            keywords = line.split(':', 1)[1].strip().split(', ')
                            if keywords:
                                if num_keywords is not None:
                                    keywords = keywords[:num_keywords]  # Limit keywords to num_keywords
                                if numbered_keywords:
                                    # Format the keywords as a numbered list
                                    numbered_keywords_text = '\n'.join(
                                        f"{i + 1}. {keyword}" for i, keyword in enumerate(keywords))
                                    modified_content.append(f"Keywords:\n{numbered_keywords_text}")
                                else:
                                    regular_keywords_text = ', '.join(keywords)
                                    modified_content.append(f"Keywords: {regular_keywords_text}")
                            else:
                                modified_content.append(line)
                        else:
                            modified_content.append(line)

                    # Join modified content to form the complete message
                    final_message = '\n'.join(modified_content)

                    # Send modified or original message content based on numbered_keywords
                    await ctx.send(final_message)
                    print(final_message)
                else:
                    error_message = await response.text()
                    await ctx.send("Failed to analyze the image.")
                    print("Error:", error_message)
    else:
        await ctx.send("Please upload an image with the command.")


# Нова команда для встановлення мови
@bot.command(name='language',
             help='Sets the language for the analyze command. Available options: "uk" for Ukrainian and "en" for English.')
async def language_command(ctx, lang: str):
    global language
    if lang in ["uk", "en"]:
        language = lang
        await ctx.send(f"Language set to: {language}")
    else:
        await ctx.send("Invalid language option. Use 'uk' for Ukrainian or 'en' for English.")


@bot.command(name='help', help='Provides information on how to use the bot.')
async def help_command(ctx):
    if language == "en":
        help_message = (
            "**Help with Bot Commands**\n\n"
            "**!language <language>** - Sets the language for the `!analyze` command. Options: 'uk' for Ukrainian and 'en' for English.\n"
            "**!analyze <title_length> <description_length> <keyword_count> <numbered_keywords>** - Analyzes an uploaded image with given parameters and allows for regular or numbered keyword lists.\n"
            "Example: `!analyze 20 100 10 True` - generates a title up to 20 characters, a description up to 100 characters, and 10 numbered keywords.\n"
            "Without 'True', keywords will be in a regular list.\n\n"
            "**!generate <prompt>** - Generates an image based on the provided text prompt.\n"
            "Example: `!generate beautiful landscape` - generates an image corresponding to the description 'beautiful landscape'.\n\n"
            "**!help** - Shows this help message."
        )
    else:
        help_message = (
            "**Допомога щодо використання бота**\n\n"
            "**!language <мова>** - Встановлює мову для команди `!analyze`. Варіанти: 'uk' для української, 'en' для англійської.\n"
            "**!analyze <довжина_назви> <довжина_опису> <кількість_ключових_слів> <нумерація_ключових_слів>** - Аналізує завантажене зображення, дозволяючи вибирати звичайний або числовий список ключових слів.\n"
            "Приклад: `!analyze 20 100 10 True` - генерує назву до 20 символів, опис до 100 символів, і 10 ключових слів з нумерацією.\n"
            "Якщо 'True' не вказано, ключові слова будуть у звичайному списку.\n\n"
            "**!generate <запит>** - Генерує зображення за вказаним текстовим запитом.\n"
            "Приклад: `!generate красивий пейзаж` - генерує зображення відповідно до опису 'красивий пейзаж'.\n\n"
            "**!help** - Показує цю допомогу."
        )

    await ctx.send(help_message)


bot.run(DISCORD_TOKEN)
