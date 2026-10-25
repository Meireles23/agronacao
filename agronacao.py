# agronacao.py - Núcleo da Plataforma AgroNação
import sys
import time
from agro_ia import AgroIA

def exibir_banner():
    print("=" * 70)
    print("      AGRONAÇÃO - Sistema Operativo Inteligente da Agropecuária     ")
    print('      Tagline: "Do solo ao mercado. Com a Agro a gerir tudo."      ')
    print("=" * 70)
    print(" Status: 100% Operacional | IA Agro: Ativa | Versão: 1.0 (Angola)")
    print(" Digite 'ajuda' para ver os comandos ou 'sair' para encerrar.\n")

def main():
    ia = AgroIA()
    exibir_banner()
    
    while True:
        try:
            entrada = input("AgroNação > ")
            if not entrada.strip():
                continue
                
            if entrada.lower() in ["sair", "exit", "quit"]:
                print("\nEncerrando a AgroNação. A otimizar dados da exploração... Até breve!")
                time.sleep(1)
                sys.exit()
                
            elif entrada.lower() in ["ajuda", "help"]:
                print("\n--- COMANDOS RÁPIDOS DISPONÍVEIS ---")
                print("1. 'Agro, qual o estado da exploração hoje?'")
                print("2. 'Agro, agenda a colheita do milho da parcela 3'")
                print("3. 'Agro, quanto gastei em fertilizante este mês?'")
                print("4. 'Agro, qual o melhor comprador para o meu feijão?'")
                print("5. 'Agro, cria uma escala de trabalho para os próximos 15 dias'\n")
                continue
                
            # Processa através da IA Agro
            resposta = ia.processar_comando(entrada)
            print(f"\n{resposta}\n")
            print("-" * 70)
            
        except KeyboardInterrupt:
            print("\nSistema interrompido com segurança.")
            sys.exit()

if __name__ == "__main__":
    main()