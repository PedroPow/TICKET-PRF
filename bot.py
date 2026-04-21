import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Select
import asyncio
from config import CANAL_ENVIO_MENU_ID, TICKET_CATEGORIAS, CARGOS_RESPONSAVEIS, GUILD_ID
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def embed_padrao(descricao, cor=discord.Color.yellow()):
    return discord.Embed(
        description=descricao,
        color=cor
    )

# ----------------- Funções utilitárias -----------------
def membro_tem_cargo_responsavel(membro: discord.Member, categoria_id: int) -> bool:
    tipo = {v: k for k, v in TICKET_CATEGORIAS.items()}.get(categoria_id)
    if not tipo:
        return False
    cargo_responsavel_id = CARGOS_RESPONSAVEIS.get(tipo)
    return discord.utils.get(membro.roles, id=cargo_responsavel_id) is not None

# ----------------- Modais -----------------
class EditarNomeModal(Modal, title="Editar Nome do Ticket"):
    novo_nome = TextInput(label="📁ㅤ•ㅤNovo nome do canal", placeholder="ex: ticket-pedropow", max_length=90)
    async def on_submit(self, interaction: discord.Interaction):
        nome = self.novo_nome.value.replace(" ", "-").lower()
        await interaction.channel.edit(name=nome)
        await interaction.response.send_message(f"✅ Nome do ticket alterado para `{nome}`.", ephemeral=True)

class ConcluirTicketModal(Modal, title="Finalizar Ticket"):
    resultado = TextInput(label="Resultado do atendimento", style=discord.TextStyle.paragraph, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        if not membro_tem_cargo_responsavel(interaction.user, interaction.channel.category_id):
            await interaction.response.send_message(
                "❌ Você não tem permissão para concluir este ticket.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        canal = interaction.channel
        membros = [p for p in canal.overwrites if isinstance(p, discord.Member)]
        membros.append(interaction.user)

        enviados = 0

        for membro in membros:
            if membro.bot:
                continue

            try:
                embed = discord.Embed(
                    title="✅ Ticket Finalizado",
                    description=(
                        f"**Ticket:** `{canal.name}`\n\n"
                        f" **Resultado do Atendimento:**\n {self.resultado.value}\n\n"
                        f"\n\n⚠️ **Observação:** Esta é uma mensagem automática. Por favor, não responda a esta DM. Se precisar de mais ajuda, abra um novo ticket no servidor. Agradecemos pela compreensão!\n\n\n"
                        f"👮🏽 **Atendido por:** {interaction.user.mention}\n\n"
                    ),
                    color=discord.Color.yellow()
                )

                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/1444735189765849320/1495965745400516708/PRF.png?ex=69e82a2b&is=69e6d8ab&hm=4874fa132517e00dc46de34d3c751c5bd6cf273b072f26d39a2ac2b97f346f6f&"
                )

                embed.set_footer(
                    text="Batalhão PRF Virtual® Todos direitos reservados.",
                    icon_url="https://cdn.discordapp.com/attachments/1496035727241121955/1496048035652964412/PRF.png"
                )

                await membro.send(embed=embed)
                enviados += 1

            except:
                pass

        await interaction.followup.send(
            f"✅ Resultado enviado via DM para `{enviados}` membros. Fechando ticket...", ephemeral=True
        )
        await asyncio.sleep(5)
        await canal.delete()

class MotivoModal(Modal):
    def __init__(self, tipo_ticket):
        super().__init__(title="Motivo da Abertura")
        self.tipo_ticket = tipo_ticket
        self.motivo = TextInput(label="Motivo", placeholder="Ex: Bug na cidade", max_length=100)
        self.add_item(self.motivo)
    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild
        categoria_id = TICKET_CATEGORIAS.get(self.tipo_ticket)
        cargo_id = CARGOS_RESPONSAVEIS.get(self.tipo_ticket)
        categoria = guild.get_channel(categoria_id)
        cargo = guild.get_role(cargo_id)
        if not categoria or not cargo:
            await interaction.response.send_message("❌ Categoria ou cargo não encontrado.", ephemeral=True)
            return
        nome_canal = f"📁・{self.tipo_ticket.upper()}・{user.name}".replace(" ", "-").lower()
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            cargo: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        canal = await guild.create_text_channel(nome_canal, category=categoria, overwrites=overwrites)
        embed = discord.Embed(
            title=f"Atendimento | Chamado de {self.tipo_ticket.upper()}",
            description=f"Olá. {user.mention}! Seja muito bem-vindo ao nosso atendimento personalizado.\n\n Estamos felizes em tê-lo aqui e faremos o possível para fornecer a ajuda que você precisa. Em breve, um dos nossos staff estará disponível para atendê-lo.\n\n Responsavel pelo atendimento:\n {cargo.mention}\n\n Assunto do Atendimento:\n `{self.motivo.value}` \n\n Agradecemos desde já pelo seu contato. Caso queira realizar alguma alteração no atendimento, fique à vontade para interagir conosco abaixo:",
            color=discord.Color.yellow()
        )    

        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1444735189765849320/1495965745400516708/PRF.png?ex=69e82a2b&is=69e6d8ab&hm=4874fa132517e00dc46de34d3c751c5bd6cf273b072f26d39a2ac2b97f346f6f&=&format=webp&quality=lossless&width=518&height=648")   

        embed.set_footer(text="Batalhão PRF Virtual® Todos direitos reservados.", icon_url="https://cdn.discordapp.com/attachments/1496035727241121955/1496048035652964412/PRF.png?ex=69e876ce&is=69e7254e&hm=25aeb6b71ed2c2d673c88a5ca4c44289fc12eea02bee3d36aab09a778ca386dd&")

        await canal.send(content=user.mention, embed=embed, view=TicketView())
        await interaction.response.send_message(f"✅ Ticket criado: {canal.mention}", ephemeral=True)


class TicketConfigSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Editar Nome", value="rename", emoji="<:EDITAR:1489108787745788014> "),
            discord.SelectOption(label="Concluir Ticket", value="finish", emoji="<:AMARELO:1496016145902338069> "),
        ]

        super().__init__(
            placeholder="Selecione uma ação...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if not membro_tem_cargo_responsavel(interaction.user, interaction.channel.category_id):
            await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)
            return

        escolha = self.values[0]

        if escolha == "assumir":
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} assumiu este ticket!", ephemeral=True
            )

        elif escolha == "add":
            view = AdicionarMembroSelectView(interaction.guild)
            await interaction.response.send_message(
                "Selecione um membro para adicionar:", view=view, ephemeral=True
            )

        elif escolha == "remove":
            membros = [m for m in interaction.channel.members if not m.bot]
            if not membros:
                await interaction.response.send_message("embed=embed", ephemeral=True)
                return

            view = RemoverMembroSelectView(interaction.guild, membros)
            await interaction.response.send_message(
                "Selecione um membro para remover:", view=view, ephemeral=True
            )

        elif escolha == "rename":
            await interaction.response.send_modal(EditarNomeModal())

        elif escolha == "finish":
            await interaction.response.send_modal(ConcluirTicketModal())     

class TicketConfigView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketConfigSelect())

# ----------------- TicketView -----------------
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Configurações", style=discord.ButtonStyle.gray, emoji="<:CONFIG:1489297902118375544>")
    async def configuracoes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not membro_tem_cargo_responsavel(interaction.user, interaction.channel.category_id):
            await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Painel de configurações do ticket:",
            view=TicketConfigView(),
            ephemeral=True
        )

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.gray, emoji= "<:x1:1496016199203684484>")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not membro_tem_cargo_responsavel(interaction.user, interaction.channel.category_id):
            await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)
            return

        await interaction.response.send_message("Ticket será fechado em 5 segundos.", "Fechado por " + interaction.user.mention, ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# ----------------- Menu de Tickets -----------------
OPCOES_TICKETS = [
    ("TICKETS DE SUPORTE", "suporte", "<:PRF:1495964314539130980>"),
    ("TICKETS DE DPM", "dpm", "<:PRF:1495964314539130980>"),
    ("TICKETS DE ORG", "org", "<:PRF:1495964314539130980>"),
]

class SelectMenu(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=label,
                value=value,
                emoji=emoji
            )
            for label, value, emoji in OPCOES_TICKETS
        ]

        super().__init__(
            placeholder="Selecione o tipo de ticket",
            min_values=1,
            max_values=1,
            options=options
        )

class SelectMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelectMenu())

# ----------------- Evento on_ready -----------------
@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")

    print("\n📡 Servidores que o bot está:")
    for guild in bot.guilds:
        print(f"➡️ {guild.name} ({guild.id})")

    guild = bot.get_guild(GUILD_ID)

    if not guild:
        print("❌ Bot não está no servidor correto.")
        return

    canal = guild.get_channel(CANAL_ENVIO_MENU_ID)

    if not canal:
        print("❌ Canal não encontrado dentro do servidor.")
        return

    print(f"✅ Canal encontrado: {canal.name}")

    async for msg in canal.history(limit=20):
        if msg.author == bot.user and msg.components:
            try:
                await msg.delete()
            except:
                pass

    embed = discord.Embed(
        title="**<:TICKET:1496086945590411444> Sistema de atendimento**",
        description="**Escolha uma opção** com base no assunto que você deseja discutir com um membro da equipe através de um ticket:\n\n"
        "> Observação:\n"
        "・Por favor, tenha em mente que cada tipo de ticket é específico para lidar com o assunto selecionado.\n"
        "・• Evite abrir um ticket sem um motivo válido, pois isso pode resultar em punições.\n",
        color=discord.Color.yellow()
    )

    embed.set_image(url="https://cdn.discordapp.com/attachments/1496035727241121955/1496047812125659236/FAIXA_TICKET_2.png?ex=69e87699&is=69e72519&hm=a0ee92dd0e1ae817b3f513c4c23e4b0473a00d1067070ad83259276ade42d94e&")

    embed.set_footer(text="Batalhão PRF Virtual® Todos direitos reservados.", icon_url="https://cdn.discordapp.com/attachments/1496035727241121955/1496048035652964412/PRF.png?ex=69e876ce&is=69e7254e&hm=25aeb6b71ed2c2d673c88a5ca4c44289fc12eea02bee3d36aab09a778ca386dd&")

    await canal.send(embed=embed, view=SelectMenuView())
    print("📨 Menu enviado com sucesso.")

# ----------------- Run -----------------
bot.run("MTQ5NTk0MjY2MDQyMTMyMDg0NA.GDIw65.WupLaFWEMz4JOLwVJERNtinx4gPnCfQuKiOTOM")
