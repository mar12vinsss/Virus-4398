import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from config import TOKEN
from myserver import sever_on

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ ตั้งค่าห้องและยศ
ROLE_ID = 1317813716544262184  # ID ยศที่ต้องแจก  
VERIFY_CHANNEL_ID = 1349017134919061504  # ห้องยืนยันตัวตน  
ADMIN_CHANNEL_ID = 1349017225293594696  # ห้องแอดมิน  

verified_users = set()

# ✅ ฟอร์มยืนยันตัวตน
class VerifyModal(discord.ui.Modal, title="✅ ใส่ข้อมูลเพื่อรับยศขอเทส"):
    name = discord.ui.TextInput(label="🎮 ชื่อในเกม", placeholder="ใส่ชื่อในเกม")
    age = discord.ui.TextInput(label="🔢 อายุ", placeholder="ใส่อายุ", style=discord.TextStyle.short)
    gender = discord.ui.TextInput(label="⚧ เพศ", placeholder="เช่น ชาย, หญิง")
    rules = discord.ui.TextInput(label="📜 อ่านกฎแล้วใช่ไหม? (พิมพ์ 'ใช่' เท่านั้น)", placeholder="พิมพ์ว่า 'ใช่'", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        if self.rules.value.strip().lower() != "ใช่":
            await interaction.response.send_message("❌ พี่ต้องพิมพ์ว่า 'ใช่' เท่านั้น!", ephemeral=True)
            return
        
        role = discord.utils.get(interaction.guild.roles, id=ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            verified_users.add(interaction.user.id)

            # ✅ ส่งข้อมูลไปห้องแอดมินแทน
            admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                embed = discord.Embed(
                    title="📢 แจ้งเตือน: สมาชิกใหม่ยืนยันตัวตน!",
                    description=(
                        f"👤 **ชื่อในเกม:** {self.name.value}\n"
                        f"🔢 **อายุ:** {self.age.value}\n"
                        f"⚧ **เพศ:** {self.gender.value}\n\n"
                        f"✍ **กรอกโดย:** {interaction.user.mention}"
                    ),
                    color=discord.Color.orange()
                )
                avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
                embed.set_thumbnail(url=avatar_url)
                await admin_channel.send(embed=embed)

            await interaction.response.send_message("✅ ยืนยันตัวตนสำเร็จ!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ไม่พบยศที่ต้องการ!", ephemeral=True)

# ✅ ปุ่มยืนยันตัวตน
class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ กดเพื่อรับยศ", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())

@bot.command(name="setupverify")
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="รับยศ",
            description="กดปุ่มด้านล่างเพื่อรับยศ!",
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=VerifyButton())
        await ctx.send("✅ ตั้งค่าปุ่มยืนยันตัวตนเรียบร้อย!")

        

# ✅ แจ้งเตือนเมื่อมีคนเข้าเซิร์ฟ
#@bot.event
#async def on_member_join(member):
#    channel = bot.get_channel(VERIFY_CHANNEL_ID)
#    if channel:
#        embed = discord.Embed(
#            title="🎉 สมาชิกใหม่!",
#            description=f"{member.mention} เข้าสู่เซิร์ฟเวอร์!\nกดปุ่มด้านล่างเพื่อรับยศ",
#            color=discord.Color.green()
#        )
#        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
#        embed.set_thumbnail(url=avatar_url)
#        await channel.send(embed=embed, view=VerifyButton())###

# Variables for looping, queue and current song
is_looping = False
song_queue = []
current_song = None
volume = 1.0  # เริ่มต้นที่ระดับเสียง 1.0 (100%)

@bot.command(name="p")
async def p(ctx, url: str):
    global current_song, song_queue, is_looping
    if not ctx.author.voice:
        await ctx.send("เข้าห้องวอยซ์ก่อนสิพรี่!")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        voice = await voice_channel.connect()
    else:
        voice = ctx.voice_client

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        url2 = info['url']
        title = info['title']

    song_queue.append((url2, title))

    if not current_song:
        await play_next(ctx, voice)

    await ctx.send(f"เพิ่มเพลงลงคิว: {title}")

async def play_next(ctx, voice):
    global current_song, song_queue, is_looping, volume
    if song_queue:
        url, title = song_queue.pop(0)
        current_song = (url, title)
        
        def after_playing(e):
            if is_looping:
                voice.play(discord.FFmpegPCMAudio(url, executable="ffmpeg"), after=after_playing)
                voice.source = discord.PCMVolumeTransformer(voice.source, volume)
            else:
                asyncio.run_coroutine_threadsafe(play_next(ctx, voice), bot.loop)

        voice.play(discord.FFmpegPCMAudio(url, executable="ffmpeg"), after=after_playing)
        voice.source = discord.PCMVolumeTransformer(voice.source, volume)
        await ctx.send(f"กำลังเล่นเพลง: {title}")
    else:
        current_song = None
        await ctx.send("ไม่มีเพลงในคิวแล้ว")

@bot.command(name="s")
async def s(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("เพลงจบแล้วเพลงไรต่อดี")
    else:
        await ctx.send("เข้าห้องดิเรียกแล้วทำไมไม่เข้าห้อง")

@bot.command(name="l")
async def l(ctx):
    global is_looping
    if ctx.voice_client:
        is_looping = not is_looping
        status = "ลูปเพลงเปิดใช้งานแล้ว" if is_looping else "ลูปเพลงถูกปิด"
        await ctx.send(status)
    else:
        await ctx.send("เข้าห้องก่อนเพลงจะ!")

@bot.command(name="q")
async def q(ctx):
    if song_queue:
        current_song = song_queue[0]
        await ctx.send(f"ตอนนี้เพลงที่กำลังรอเล่นคือ: {current_song[1]}")
    else:
        await ctx.send("คิวเพลงว่างเปล่า")

@bot.command(name="sk")
async def sk(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("ข้ามเพลงไปแล้ว")
        await play_next(ctx, ctx.voice_client)
    else:
        await ctx.send("ไม่มีเพลงเล่นอยู่ในขณะนี้")

@bot.command(name="-")
async def mute(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source)
        ctx.voice_client.source.volume = 0.0
        await ctx.send("บอทปิดเสียงแล้ว")
    else:
        await ctx.send("ไม่มีเพลงเล่นอยู่ในขณะนี้")

@bot.command(name="v")
async def vol(ctx, volume_level: int):
    global volume
    if ctx.voice_client and ctx.voice_client.is_playing():
        volume = max(0.0, min(volume_level / 100.0, 1.0))
        ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source)
        ctx.voice_client.source.volume = volume
        await ctx.send(f"ปรับเสียงเป็น {volume_level}%")
    else:
        await ctx.send("ไม่มีเพลงเล่นอยู่ในขณะนี้")

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None and member == bot.user:
        # เมื่อบอทเข้าห้องเสียง ให้ปรับเสียงให้เป็น 100%
        voice_client = bot.voice_clients[0]  # ใช้ voice client ของบอท
        voice_client.source.volume = 1.0  # ปรับเสียงบอทให้เป็น 100%
        print(f"บอทเข้าห้องเสียง: {after.channel.name} และตั้งเสียงเป็น 100%")

# ✅ แจ้งแอดมินตอนบอทออนไลน์
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} ออนไลน์แล้ว!")
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel:
        await admin_channel.send("✅ บอทออนไลน์แล้ว!")

server_on()       

bot.run(os.getenv('TOKEN'))
