import discord
from discord import app_commands
from discord.ext import tasks
from func import *
import traceback
import random
import asyncio
import os
import shutil
from itertools import cycle

class captcha(discord.ui.Modal, title='Верификация'):

    name = discord.ui.TextInput(
        label=f'Введите свой капча-код:',
        placeholder='123456789',
    )

    async def on_submit(self, interaction: discord.Interaction):
        config = load_json(f"guilds/{interaction.guild.id}/config.json")
        role = interaction.guild.get_role(int(config['role']))
        inputcode = self.children[0].value
        codes = load_json(f"guilds/{interaction.guild.id}/users.json")
        userdata = codes[str(interaction.user.id)]
        if inputcode == userdata:
            embed = discord.Embed(title=f"Уважаемый пользователь!", description=f"Спасибо, Вы успешно прошли проверку. Добро пожаловать, {interaction.user.name}!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            codes = load_json(f"guilds/{interaction.guild.id}/users.json")
            status = 'verified'
            codes[str(interaction.user.id)] = str(status)
            write_json(f"guilds/{interaction.guild.id}/users.json", codes)
            await interaction.user.add_roles(role)
            embed = discord.Embed(title=f"{interaction.user.name} успешно прошёл прошёл проверку!", description=f"Пользователь успешно прошёл капчу и был допущен к серверу!", color=discord.Color.green())
            channel = interaction.guild.get_channel(int(config['logchannel']))
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(title=f"Уважаемый пользователь!", description=f"Вы были кикнуты с сервера **{interaction.guild.name}**,\nтак как Вы неверно ввели свой капча-код!")
            await interaction.user.send(embed=embed)
            await interaction.user.kick(reason='Неверно введён индивидуальный капча-код')
            embed = discord.Embed(title=f"{member.name} был кикнут.", description=f"Пользователь был кикнут, так как не прошёл проверку на робота (индивидуальный капча-код бл введён не верно!)", color=discord.Color.red())
            channel = interaction.guild.get_channel(int(config['logchannel']))
            await channel.send(embed=embed)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        config = load_json(f"guilds/{interaction.guild.id}/config.json")
        channel = interaction.guild.get_channel(int(config['logchannel']))
        await channel.send(f'Вы сейчас на своих глазах видите ошибку. Её лог:\n{error}\nПожалуйста, сообщите об этой ошибке разработчику <@553960665581355009>! Будем благодарны за содействие.')
        traceback.print_tb(error.__traceback__)

class captcha_btn(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Начать проверку", style=discord.ButtonStyle.primary, custom_id="verify", emoji="🤖")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        codes = load_json(f"guilds/{guild_id}/users.json")
        config = load_json(f"guilds/{guild_id}/config.json")
        try:
            role = interaction.guild.get_role(int(config['role']))
            rname = role.name
        except:
            await interaction.response.send_message(f"Извините, но я не могу вас верифицировать. Настроенная роль либо отсутствуют, либо у меня недостаточно прав. Сообщите об этом владельцу сервера!", ephemeral=True)
        if codes[f'{interaction.user.id}'] == 'notverified':
            status = random.randint(100000000, 999999999)
            codes[str(interaction.user.id)] = str(status)
            write_json(f"guilds/{guild_id}/users.json", codes)
            embed = discord.Embed(title=f"Уважаемый пользователь!", description=f"Вы получили свой капча-код: ||{status}||\nВы должны его ввести прямо сейчас, нажав на кнопку ещё раз.\n\n**У вас всего 15 минут после присоединения к серверу!**")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            channel = interaction.guild.get_channel(int(config['logchannel']))
            embed = discord.Embed(title=f"{interaction.user.name} получил свой капча-код", description="Данный пользователь получил свой индивидуальный капча-код!", color=discord.Color.purple())
            await channel.send(embed=embed)
        else:
            userdata = load_json(f"guilds/{guild_id}/users.json")
            if userdata[f'{interaction.user.id}'] == "verified":
                await interaction.response.send_message(f"Извините, но Вы уже верифицированны!", ephemeral = True)
                await interaction.user.add_roles(role)
            else:
                await interaction.response.send_modal(captcha())
                channel = interaction.guild.get_channel(int(config['logchannel']))
                embed = discord.Embed(title=f"{interaction.user.name} начал прохождение проверки", description="Данный пользователь начал прохождение проверки на робота!", color=discord.Color.blue())
                await channel.send(embed=embed)

class aclient(discord.Client):
    def __init__(self):
        super().__init__(intents = discord.Intents.all())
        self.synced = False
        self.added = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await slash.sync()
            self.synced = True
        if not self.added:
            self.add_view(captcha_btn())
            self.added = True
        change_status.start()
        check_blacklist.start()
        print(f'Бот успешно запущен под данными: {self.user} (ID: {self.user.id})')
        print('------')

    async def on_member_join(self, member):
        try:
            guild_id = member.guild.id
            config = load_json(f"guilds/{guild_id}/config.json")
            if config['channelcaptcha'] != "none":
                if member.bot is True:
                    if config['ignorebots'] == "true":
                        pass
                    else:
                        if config['lockserver'] == "true":
                            await member.kick(reason="Сервер заблокирован владельцем")
                else:
                    if config['lockserver'] == "true":
                        embed = discord.Embed(title=f"Упс...", description=f"Простите, но Вы не можете заходить на сервер **{member.guild.name}**, так как он заблокирован владельцем.", color=discord.Color.red())
                        await member.send(embed=embed)
                        await member.kick(reason="Сервер заблокирован владельцем")
                        embed = discord.Embed(title=f"{member.name} был кикнут.", description=f"Пользователь был кикнут, так как сервер был заблокирован администратором.", color=discord.Color.red())
                        channel = member.guild.get_channel(int(config['logchannel']))
                        await channel.send(embed=embed)
                    else:
                        guild = member.guild
                        channel = guild.get_channel(int(config['logchannel']))
                        embed = discord.Embed(title=f"{member.name} присоединился к серверу", description="Данный пользователь присоединился к серверу!", color=discord.Color.green())
                        await channel.send(embed=embed)
                        users = load_json(f"guilds/{guild_id}/users.json")
                        users[f'{member.id}'] = 'notverified'
                        write_json(f"guilds/{guild_id}/users.json", users)
                        await asyncio.sleep(900)
                        users = load_json(f"guilds/{guild_id}/users.json")
                        if users[str(member.id)] != "leaved":
                            codes = load_json(f"guilds/{guild_id}/users.json")
                            userdata = codes[str(member.id)]
                            if userdata != 'verified':
                                await member.kick(reason='Индивидуальный капча-код не был введён в течении 15 минут')
                                embed = discord.Embed(title=f"{member.name} был кикнут.", description=f"Пользователь был кикнут, так как не прошёл проверку на робота в течении заданного времени (15 минут)", color=discord.Color.red())
                                channel = member.guild.get_channel(int(config['logchannel']))
                                await channel.send(embed=embed)
                        else:   
                            codes = load_json(f"guilds/{guild_id}/users.json")
                            codes.pop(str(member.id))
                            write_json(f"guilds/{guild_id}/users.json", codes)
        except:
            try:
                await member.guild.owner.send('Произошла ошибка, когда пользователь присоединился к вашему серверу. Возможно, у меня нет прав на получение данных сервера, либо отсутствуют файлы конфигурации. Пожалуйста, настройте меня для стабильной работы!')
            except:
                pass

    async def on_member_remove(self, member):
        try:
            guild_id = member.guild.id
            guild = member.guild
            status = "leaved"
            users = load_json(f"guilds/{guild_id}/users.json")
            users[str(member.id)] = str(status)
            write_json(f"guilds/{guild_id}/users.json", users)
            config = load_json(f"guilds/{guild_id}/config.json")
            channel = guild.get_channel(int(config['logchannel']))
            embed = discord.Embed(title=f"{member.name} покинул сервер", description="Данный пользователь покинул данный сервер!", color=discord.Color.green())
            await channel.send(embed=embed)
        except:
            pass

    async def on_guild_join(self, guild):
        guild_id = guild.id

        try:
            channel = await guild.create_text_channel("splash-bot-информация")
            await channel.set_permissions(guild.default_role, send_messages=False)
            await channel.set_permissions(guild.default_role, view_channel=False)
            await channel.send(f"{guild.owner.mention}")
            embed = discord.Embed(title=f"Внимание!", description=f"К Вам пригласили бота верификации **Splash!**, он же сплэшик :D\nИдёт настройка вашего сервера для правильной работы верификации. Пройдёт 2 этапа:\n``Создание файлов на сервере`` - создание конфигурационного файла, а так же файла со всеми участниками сервера\n``Обработка пользователей`` - занесение пользователей в наш сервер для получения их списка\n\nНастройка сервера начнётся через 10 секунд...", color=discord.Color.blue())
            await channel.send(embed=embed)
            path = f"guilds/{guild_id}"
            os.mkdir(path)
            await asyncio.sleep(10)
            shutil.copy('samples/guild_configuration.json', f'guilds/{guild.id}/config.json')
            shutil.copy('samples/guild_users.json', f'guilds/{guild.id}/users.json')
            embed = discord.Embed(title=f"Идёт настройка...", description=f"Этап 1 - ``Создание файлов``", color=discord.Color.blue())
            await channel.send(embed=embed)
            members_int = 0
            members = len(list(guild.members))
            for member in guild.members:
                members_int = members_int + 1
                users = load_json(f"guilds/{guild_id}/users.json")
                status = "verified"
                users[str(member.id)] = str(status)
                write_json(f"guilds/{guild_id}/users.json", users)
                embed = discord.Embed(title=f"Идёт настройка...", description=f"Статус обработки участников: ``{members_int} / {members}``. Как только цифры перестанут меняться - бот окончит настройку", color=discord.Color.blue())
                await channel.send(embed=embed)
                if members_int == members:
                    embed = discord.Embed(title=f"Настройка завершена!", description=f"Вам осталось настроить до конца бота через слэш-команды и начать им пользоваться!", color=discord.Color.green())
                    await channel.send(embed=embed)
        except:
            try:
                await guild.owner.send("К вам пригласили бота Splash! Вы видите данное сообщение потому, что произошла ошибка, и возможно у бота недостаточно прав. Пожалуйста, переавторизуйте бота (кикните бота и перейдите по ссылке OAuth2 Discord(-а)) с правами администратора, иначе бот не сможет работать стабильно без прав.")
            except:
                pass
            
    async def on_guild_remove(self, guild):
        try:
            shutil.rmtree(f'guilds/{guild.id}')
        except:
            pass

client = aclient()
slash = discord.app_commands.CommandTree(client)

@slash.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    if isinstance(error, discord.app_commands.errors.MissingPermissions):
        embed = discord.Embed(title=f"Ошибка", description=f"У вас нет прав на использование данной команды ``(manage_guild, kick_members)``.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(title=f"Произошла ошибка", description=f"Произошла неизвестная ошибка! Сообщите о ней разработчику <@553960665581355009> !\nЛог ошибки:\n\n``{error}``", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

@slash.command(name='config-info', description='Информация о конфигурации сервера')
@app_commands.checks.has_permissions(manage_guild=True)
async def config_info(interaction: discord.Interaction):
    config = load_json(f"guilds/{interaction.guild.id}/config.json")
    embed = discord.Embed(title=f"Конфигурация сервера {interaction.guild.name}", description=f"Прежде чем посмотреть конфигурацию, изучите знаки обозначения:\n``true`` - правда (включено)\n``false`` - ложь (выключено)\n``none`` - не настроено\n\n\n``Роль для выдачи`` - {config['role']}\n\n``Канал для логов`` - {config['logchannel']}\n\n``Канал для верификации`` - {config['channelcaptcha']}\n\n``Игнорировать ботов от блокировки сервера?`` - {config['ignorebots']}\n\n``Заблокирован ли сервер?`` - {config['lockserver']}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@slash.command(name='config-send', description='Отправить сообщение о проверке')
@app_commands.checks.has_permissions(manage_guild=True)
async def config_send(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    config = load_json(f"guilds/{guild_id}/config.json")
    if config['ignorebots'] == "none":
        embed = discord.Embed(title=f"Ошибка", description=f"Вы не указали, стоит ли мне игнорировать ботов от блокировки сервера, либо же нет!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
    else:
        if config['lockserver'] == "none":
            embed = discord.Embed(title=f"Ошибка", description=f"Вы ещё не активировали команду переключения блокировки сервера!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
        else:
            if config['channelcaptcha'] == "none":
                embed = discord.Embed(title=f"Ошибка", description=f"Вы ещё не указали канал, в который будет отправлено сообщение о проверке!", color=discord.Color.red())
                await interaction.response.send_message(embed=embed)
            else:
                if config['logchannel'] == "none":
                    embed = discord.Embed(title=f"Ошибка", description=f"Вы ещё не указали канал, в который будут отсылаться логи (отчёты)!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed)
                else:
                    if config['role'] == "none":
                        embed = discord.Embed(title=f"Ошибка", description=f"Вы ещё не указали роль, которая будет выдана пользователю если он пройдёт проверку!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed)
                    else:
                        if config['text'] == "none":
                            embed = discord.Embed(title=f"Ошибка", description=f"Вы ещё не установили текст, который будет в сообщении о проверке!", color=discord.Color.red())
                            await interaction.response.send_message(embed=embed)
                        else:
                            embed = discord.Embed(title=f"Верификация", description=f"{config['text']}", color=discord.Colour.blue())
                            channel = interaction.guild.get_channel(int(config['channelcaptcha']))
                            await channel.send(embed=embed, view=captcha_btn())
                            await interaction.response.send_message(f"Готово! Вы успешно настроили сообщение о проверке.")

@slash.command(name='config', description='Настроить конфигурацию сервера')
@app_commands.rename(text="text")
@app_commands.describe(text="Текст, который будет размещён в сообщении о проверке")
@app_commands.rename(role="role")
@app_commands.describe(role="Роль, которая будет выдана в случае успешной верификации")
@app_commands.rename(logchannel="logschannel")
@app_commands.describe(logchannel="Канал, в котором будут логи о верификации")
@app_commands.rename(verifychannel="verifychannel")
@app_commands.describe(verifychannel="Канал, в котором будет сообщение о проверке")
@app_commands.checks.has_permissions(manage_guild=True)
async def config_text(interaction: discord.Interaction, text: str, role: discord.Role, logchannel: discord.TextChannel, verifychannel: discord.TextChannel):
    if len(text) > 300:
        await interaction.response.send_message(f"Вы не можете ставить текст сообщения более 300 символов!")
    else:
        config = load_json(f"guilds/{interaction.guild.id}/config.json")
        config['text'] = str(text)
        write_json(f"guilds/{interaction.guild.id}/config.json", config)
        config['role'] = str(role.id)
        write_json(f"guilds/{interaction.guild.id}/config.json", config)
        config['logchannel'] = str(logchannel.id)
        write_json(f"guilds/{interaction.guild.id}/config.json", config)
        config['channelcaptcha'] = str(verifychannel.id)
        write_json(f"guilds/{interaction.guild.id}/config.json", config)
        embed = discord.Embed(title=f"Успешно", description=f"Вы настроили текст сообщения о проверке как:\n``{text}``\nРоль после успешной проверки: {role.mention}\nКанал для логов: <#{logchannel.id}>\nКанал где будет сообщение о проверке: <#{verifychannel.id}>", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

@slash.command(name='ignorebots', description='Переключить игнорирование ботов при заблокированом сервере')
@app_commands.checks.has_permissions(manage_guild=True)
async def config_ignorebots(interaction: discord.Interaction):
    config = load_json(f"guilds/{interaction.guild.id}/config.json")
    if config['ignorebots'] == "none":
        config['ignorebots'] = "true"
        write_json(f"guilds/{interaction.guild.id}/config.json", config)
        embed = discord.Embed(title=f"Успешно", description=f"Теперь я буду игнорировать входящих на сервер ботов, пока сервер будет в блокировке!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        if config['ignorebots'] == "true":
            config['ignorebots'] = "false"
            write_json(f"guilds/{interaction.guild.id}/config.json", config)
            embed = discord.Embed(title=f"Успешно", description=f"Теперь, я пока не буду игнорировать входящих на сервер ботов, пока сервер будет в блокировке!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
        else:
            config['ignorebots'] = "true"
            write_json(f"guilds/{interaction.guild.id}/config.json", config)
            embed = discord.Embed(title="Успешно", description="Теперь, я буду игнорировать входящих на сервер ботов, пока сервер будет в блокировке!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)

@slash.command(name='lockserver', description='Переключить блокирование сервера от входящих на сервер участников')
@app_commands.checks.has_permissions(manage_guild=True)
async def config_lockserver(interaction: discord.Interaction):
    config = load_json(f"guilds/{interaction.guild.id}/config.json")
    if config['lockserver'] == "none":
        config['lockserver'] = "false"
        write_json(f"guilds/{interaction.guild.id}/config.json", config)
        embed = discord.Embed(title="Успешно", description="Команда активирована. Сервер сейчас разблокирован!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        if config['lockserver'] == "true":
            config['lockserver'] = "false"
            write_json(f"guilds/{interaction.guild.id}/config.json", config)
            embed = discord.Embed(title="Успешно", description="Вы успешно разблокировали сервер. Теперь новые участники вновь смогут заходить на сервер!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
        else:
            config['lockserver'] = "true"
            write_json(f"guilds/{interaction.guild.id}/config.json", config)
            embed = discord.Embed(title="Успешно", description="Вы успешно заблокировали сервер. Теперь новые участники не смогут сюда входить, пока Вы сами не разблокируете сервер!")
            await interaction.response.send_message(embed=embed)

@slash.command(name='help', description='Справочник по всем командам')
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title=f"Командный справочник", description=f"``/verify`` - верифицирует пользователя вручную (требуется право Выгонять участников (Kick Members))\n``/config`` - указывает канал логов, верификации, роль верификацированного пользователя, текст сообщения о проверке\n``/config-save`` - сохраняет файл конфигурации\n``/config-load`` - выгружает сохранённый файл конфигурации\n``/ignorebots`` - автоматически переключает игнорирование входа бота на сервер в случае его блокировки\n``/lockserver`` - блокирует сервер или ещё запрещает входить новым участникам на сервер\n``/config-info`` - показывает текущую конфигурацию сервера\n``/config-send`` - отправляет сообщение о проверке в заданный вами канал \n\n**Для использования всех указаных команд, вам необходимо иметь право Управление сервером (Manage Guild)!**", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@slash.command(name='verify', description='Верифицировать пользователя вручную')
@app_commands.rename(member="member")
@app_commands.describe(member="Пользователь, которого вы хотите верифицировать вручную")
@app_commands.checks.has_permissions(kick_members=True)
async def verify_member(interaction: discord.Interaction, member: discord.Member):
    users = load_json(f"guilds/{interaction.guild.id}/users.json")
    config = load_json(f"guilds/{interaction.guild.id}/config.json")
    role = interaction.guild.get_role(int(config['role']))
    if users[f'{member.id}'] == 'verified':
        embed = discord.Embed(title="Ошибка", description=f"Пользователь {member.mention} уже верифицирован!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
    else:
        if users[f'{member.id}'] == 'notverified':
            users[f'{member.id}'] = 'verified'
            write_json(f"guilds/{interaction.guild.id}/users.json", users)
            await member.add_roles(role)
            embed = discord.Embed(title="Успешно", description=f"Пользователь {member.mention} был успешно верифицирован!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
            embed = discord.Embed(title="Верификация вручную", description=f"Пользователь {interaction.user.mention} верифицировал пользователя {member.mention}!", color=discord.Color.green())
            channel = interaction.guild.get_channel(int(config['logchannel']))
            await channel.send(embed=embed)
        else:
            users[f'{member.id}'] = 'verified'
            write_json(f"guilds/{interaction.guild.id}/users.json", users)
            await member.add_roles(role)
            embed = discord.Embed(title="Успешно", description=f"Пользователь {member.mention} был успешно верифицирован!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
            embed = discord.Embed(title="Верификация вручную", description=f"Пользователь {interaction.user.mention} верифицировал пользователя {member.mention}!", color=discord.Color.green())
            channel = interaction.guild.get_channel(int(config['logchannel']))
            await channel.send(embed=embed)

@slash.command(name='blacklist-add', description='Занести гильдию в чёрный список (доступно разработчику)')
@app_commands.rename(guild="guild")
@app_commands.describe(guild="ID гильдии")
async def blacklist_add(interaction: discord.Interaction, guild: str):
    if interaction.user.id == 553960665581355009:
        blacklist = load_json("blacklist.json")
        if int(guild) in blacklist['list']:
            embed = discord.Embed(title=f"Ошибка", description=f"Данный ID гильдии уже находится в чёрном списке!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
        else:
            blacklist['list'].append(int(guild))
            write_json("blacklist.json", blacklist)
            embed = discord.Embed(title=f"Успешно", description=f"Данный ID гильдии был успешно занесён в чёрный список!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title=f"Ошибка", description=f"Данную команду может использовать только разработчик бота!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@slash.command(name='blacklist-remove', description='Удалить гильдию из чёрного списка (доступно только разработчику)')
@app_commands.rename(guild="guild")
@app_commands.describe(guild="ID гильдии")
async def blacklist_remove(interaction: discord.Interaction, guild: str):
    if interaction.user.id == 553960665581355009:
        blacklist = load_json("blacklist.json")
        if int(guild) not in blacklist['list']:
            embed = discord.Embed(title=f"Ошибка", description=f"Данный ID гильдии не найден в чёрном списке!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
        else:
            blacklist['list'].remove(int(guild))
            write_json("blacklist.json", blacklist)
            embed = discord.Embed(title=f"Успешно", description=f"Данный ID гильдии был успешно удалён из чёрного списка!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title=f"Ошибка", description=f"Данную команду может использовать только разработчик бота!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@slash.command(name='guilds', description='Посмотреть список гильдий (доступно только разработчику)')
async def guilds_list(interaction: discord.Interaction):
    if interaction.user.id == 553960665581355009:
        embed = discord.Embed(title=f"Список всех гильдий", description=f"{client.guilds}", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title=f"Ошибка", description=f"Данную команду может использовать только разработчик бота!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@slash.command(name='leave-guild', description='Выйти из определённой гильдии (доступно только разработчику)')
@app_commands.rename(guild="guild")
@app_commands.describe(guild="ID гильдии")
@app_commands.rename(reason="reason")
@app_commands.describe(reason="Причина")
async def leave_guild_for_id(interaction: discord.Interaction, guild: str, reason: str):
    if interaction.user.id == 553960665581355009:
        yguild = await client.fetch_guild(int(guild))
        try:
            await yguild.owner.send(f"Бот покинул ваш сервер, так как разработчик ввёл команду выхода. Причина:\n``{reason}``")
        except:
            pass
        await yguild.leave()
        embed = discord.Embed(title=f'Успешно', description=f'Бот успешно покинул гилдию под ID: {guild} !')
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title=f"Ошибка", description=f"Данную команду может использовать только разработчик бота!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@slash.command(name='server-info', description='Полная информация о сервере')
async def server_info(interaction: discord.Interaction):
    all = len(interaction.guild.members)
    members = len(list(filter(lambda m: not m.bot, interaction.guild.members)))
    bots = len(list(filter(lambda m: m.bot, interaction.guild.members)))
    statuses = [len(list(filter(lambda m: str(m.status) == "online", interaction.guild.members))),
                len(list(filter(lambda m: str(m.status) == "idle", interaction.guild.members))),
                len(list(filter(lambda m: str(m.status) == "dnd", interaction.guild.members))),
                len(list(filter(lambda m: str(m.status) == "offline", interaction.guild.members)))]
    embed = discord.Embed(title=f"{interaction.guild.name} Справка по серверу", description="Информация о сервере", color=discord.Colour.blue())
    embed.add_field(name='🆔 ID сервера', value=f"{interaction.guild.id}", inline=False)
    embed.add_field(name="💡 Статусы пользователей", value=f"В сети: {statuses[0]} | Неактивны: {statuses[1]} | Не беспокоить: {statuses[2]} | Оффлайн: {statuses[3]}", inline=False)
    embed.add_field(name="👥 Участники", value=f"Всех: {all} | Людей: {members} | Ботов: {bots}", inline=False)
    embed.add_field(name='📆 Дата создания сервера', value=interaction.guild.created_at.strftime("%b %d %Y"), inline=False)
    embed.add_field(name='👑 Владелец', value=f"<@{interaction.guild.owner_id}>", inline=False)
    embed.add_field(name='💬 Каналы', value=f'{len(interaction.guild.text_channels)} Текстовый(-ых) | {len(interaction.guild.voice_channels)} Голосовой(-ых)', inline=False)
    embed.add_field(name='🌎 Регион', value=f'Российская Федерация', inline=False)
    embed.set_thumbnail(url=interaction.guild.icon)  
    await interaction.response.send_message(embed=embed)

@slash.command(name='config-save', description='Создаёт резервную копию конфигурации сервера')
@app_commands.checks.has_permissions(manage_guild=True)
async def create_backup(interaction: discord.Interaction):
    try:
        os.mkdir(f"saves/{interaction.guild.id}")
        shutil.copy(f'guilds/{interaction.guild.id}/config.json', f'saves/{interaction.guild.id}/config.json')
        embed = discord.Embed(title="Успешно", description="Конфигурация данного сервера успешно сохранена! :white_check_mark: ", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    except:
        shutil.rmtree(f"saves/{interaction.guild.id}")
        os.mkdir(f"saves/{interaction.guild.id}")
        shutil.copy(f'guilds/{interaction.guild.id}/config.json', f'saves/{interaction.guild.id}/config.json')
        embed = discord.Embed(title="Успешно", description="Конфигурация данного сервера успешно сохранена! :white_check_mark: ", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

@slash.command(name='config-load', description='Загрузить резервную копию конфигурации сервера')
@app_commands.checks.has_permissions(manage_guild=True)
async def load_backup(interaction: discord.Interaction):
    try:
        shutil.copy(f'saves/{interaction.guild.id}/config.json', f'guilds/{interaction.guild.id}/config.json')
        embed = discord.Embed(title="Успешно", description="Резервная копия данного сервера была успешно загружена!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    except:
        embed = discord.Embed(title="Ошибка", description="Вы не создавали резервную копию данного сервера!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

@tasks.loop(seconds=2)
async def change_status():
    url = "https://www.youtube.com/watch?v=Khe3jIWqN0c"
    guilds = len(list(client.guilds))
    activity = discord.Game(name=f"Я нахожусь на {guilds} серверах | /help")
    await client.change_presence(status=discord.Status.idle, activity=activity)

@tasks.loop(seconds=3)
async def check_blacklist():
    blacklist = load_json("blacklist.json")
    for guild in client.guilds:
        if guild.id in blacklist['list']:
            embed = discord.Embed(title='Вы в чёрном списке!', description=f'Ваш сервер {guild.name} находится в чёрном списке бота! Я покидаю вас и ваш сервер.', color=discord.Color.red())
            await guild.owner.send(embed=embed)
            await guild.leave()

bot = load_json("config.json")
client.run(bot['token'])