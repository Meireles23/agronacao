# agro_ia.py - O Cérebro da IA Agro (Atualizado com Módulo de Campo)
import datetime
from modulo_campo import ModuloCampo

class AgroIA:
    def __init__(self):
        self.nome_ia = "Agro"
        self.versao = "1.1.0-Angola"
        self.campo = ModuloCampo()
        
    def processar_comando(self, comando):
        cmd = comando.lower().strip()
        
        if "parcela" in cmd or "sensores" in cmd or "humidade" in cmd:
            # Extrai o número da parcela se mencionado
            if "1" in cmd:
                return self.campo.ler_sensores("1")
            elif "2" in cmd:
                return self.campo.ler_sensores("2")
            elif "3" in cmd:
                return self.campo.ler_sensores("3")
            else:
                return self.campo.ler_sensores("1") # Padrão
                
        elif "praga" in cmd or "doença" in cmd or "inseto" in cmd:
            return self.campo.verificar_pragas()
            
        elif "estado" in cmd or "resumo" in cmd:
            return (
                "🌿 [Relatório Geral da Exploração - AgroNação]\n"
                "- Sensores Ativos em Campo: 12\n"
                "- Clima Atual: Estável em todo o território monitorizado.\n"
                "- Alertas: 1 aviso preventivo no PragaAlerta (Parcela 2).\n"
                "Digite 'ver sensor parcela 2' ou 'verificar pragas' para detalhes."
            )
            
        elif "colheita" in cmd or "agenda" in cmd:
            return (
                "📅 [Agendamento Inteligente]\n"
                "A colheita do milho da Parcela 3 foi agendada com sucesso para a próxima terça-feira.\n"
                "Notificação automática enviada para a equipa de campo."
            )
            
        elif "fertilizante" in cmd or "custo" in cmd:
            return (
                "💰 [Gestão Financeira & Stocks]\n"
                "- Gasto em fertilizantes este mês: 450.000 Kz\n"
                "- Retorno Estimado (ROI): +28% com base no rendimento esperado da safra atual."
            )
            
        elif "comprador" in cmd or "mercado" in cmd:
            return (
                "📈 [FazendaDirecta - Oportunidade de Mercado]\n"
                "O melhor comprador para o seu feijão esta semana é a 'Rede de Supermercados Kifica' "
                "com proposta de 850 Kz/kg (Contrato verificado e seguro)."
            )
            
        elif "escala" in cmd or "trabalho" in cmd:
            return (
                "👥 [AgroGestão - Recursos Humanos]\n"
                "Escala de trabalho para os próximos 15 dias gerada com sucesso.\n"
                "Equipa A: Manutenção e Irrigação | Equipa B: Controlo Pragas e Adubação."
            )
            
        else:
            return (
                f"🤖 Olá! Sou a {self.nome_ia}, o seu sistema operativo inteligente.\n"
                "Pode testar novos comandos como:\n"
                "• 'Ver sensor parcela 2'\n"
                "• 'Verificar pragas'\n"
                "• 'Estado da exploração'\n"
                "• 'Melhor comprador'"
            )