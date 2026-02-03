"""Seed the knowledge base with sample automotive documentation."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import async_session
from src.rag.pipeline import RAGPipeline


# ============== Sample Documentation ==============

VEHICLE_SPECS = """
# Especificações Técnicas - Modelo GenAuto X1 2024

## Motor
- **Tipo**: 1.0 TSI Turbo Flex
- **Potência**: 128 cv (gasolina) / 116 cv (etanol)
- **Torque**: 200 Nm
- **Cilindrada**: 999 cm³
- **Alimentação**: Injeção direta de combustível
- **Combustível**: Flex (gasolina/etanol)

## Transmissão
- **Tipo**: Automática de 6 velocidades
- **Tração**: Dianteira
- **Modos de condução**: Normal, Sport, Eco

## Dimensões
- **Comprimento**: 4.199 mm
- **Largura**: 1.760 mm
- **Altura**: 1.568 mm
- **Entre-eixos**: 2.651 mm
- **Porta-malas**: 373 litros (420L com banco rebatido)

## Peso e Capacidades
- **Peso em ordem de marcha**: 1.239 kg
- **Capacidade do tanque**: 50 litros
- **Capacidade de reboque**: 750 kg (freado)

## Consumo (INMETRO)
- **Cidade (gasolina)**: 12,4 km/l
- **Estrada (gasolina)**: 14,2 km/l
- **Cidade (etanol)**: 8,6 km/l
- **Estrada (etanol)**: 10,1 km/l

## Pneus e Rodas
- **Medida dos pneus**: 205/60 R16
- **Rodas**: Liga leve 16"
- **Estepe**: Temporário (uso emergencial até 80 km/h)
"""

MAINTENANCE_GUIDE = """
# Guia de Manutenção - GenAuto X1

## Revisões Programadas

### Revisão de 10.000 km ou 12 meses
- Troca de óleo do motor
- Substituição do filtro de óleo
- Verificação do filtro de ar
- Inspeção dos freios
- Verificação dos níveis de fluidos
- **Custo estimado**: R$ 450,00

### Revisão de 20.000 km ou 24 meses
- Todos os itens da revisão de 10.000 km
- Troca do filtro de ar do motor
- Troca do filtro de ar condicionado
- Verificação das correias
- Alinhamento e balanceamento
- **Custo estimado**: R$ 650,00

### Revisão de 40.000 km ou 48 meses
- Todos os itens anteriores
- Troca das velas de ignição
- Troca do fluido de freio
- Inspeção da suspensão
- **Custo estimado**: R$ 950,00

### Revisão de 60.000 km
- Todos os itens anteriores
- Troca da correia do alternador
- Verificação do sistema de arrefecimento
- Inspeção do escapamento
- **Custo estimado**: R$ 1.200,00

## Intervalos de Troca

| Item | Intervalo |
|------|-----------|
| Óleo do motor | 10.000 km ou 12 meses |
| Filtro de óleo | 10.000 km ou 12 meses |
| Filtro de ar | 20.000 km ou 24 meses |
| Filtro de combustível | 40.000 km |
| Velas de ignição | 40.000 km |
| Fluido de freio | 40.000 km ou 24 meses |
| Fluido de arrefecimento | 60.000 km ou 48 meses |
| Correia dentada | 100.000 km |

## Óleo Recomendado
- **Especificação**: SAE 5W-30 API SN
- **Capacidade com filtro**: 4,2 litros
- **Marcas homologadas**: Castrol, Mobil, Shell, Petronas
"""

TROUBLESHOOTING_GUIDE = """
# Guia de Diagnóstico - Problemas Comuns

## Luz de Check Engine Acesa

### Causas Comuns
1. **Tampa do tanque solta**
   - Sintoma: Luz acende após abastecer
   - Solução: Verificar e apertar a tampa do tanque
   - Gravidade: Baixa

2. **Sensor de oxigênio (sonda lambda)**
   - Sintoma: Aumento no consumo, marcha lenta irregular
   - Solução: Substituição do sensor
   - Custo médio: R$ 300-500
   - Gravidade: Média

3. **Catalisador**
   - Sintoma: Perda de potência, cheiro de enxofre
   - Solução: Verificação e possível substituição
   - Gravidade: Alta (procure assistência imediatamente)

4. **Bobina de ignição**
   - Sintoma: Motor falhando, perda de potência
   - Solução: Diagnóstico e troca da bobina defeituosa
   - Gravidade: Média

## Problemas de Freio

### Freio Fazendo Barulho
- **Chiado ao frear**: Pastilhas possivelmente gastas
  - Verificar espessura das pastilhas (mínimo 3mm)
  - Substituir se necessário
  
- **Ruído metálico**: Disco pode estar empenado ou gasto
  - Verificar espessura do disco
  - Retificar ou substituir

### Pedal de Freio Mole
- Verificar nível do fluido de freio
- Possível ar no sistema (necessário sangria)
- Verificar cilindro mestre
- **ATENÇÃO**: Não dirija com freio comprometido!

## Superaquecimento do Motor

### Ações Imediatas
1. Ligue o ar quente no máximo (ajuda a dissipar calor)
2. Desligue o ar condicionado
3. Pare em local seguro
4. NUNCA abra o reservatório com motor quente
5. Aguarde esfriar (mínimo 30 minutos)

### Causas Comuns
- Nível baixo de fluido de arrefecimento
- Vazamento no sistema
- Termostato travado
- Ventoinha não funcionando
- Bomba d'água defeituosa

## Bateria Descarregada

### Como dar partida com chupeta
1. Conecte o cabo vermelho (+) na bateria boa
2. Conecte a outra ponta do vermelho (+) na bateria descarregada
3. Conecte o cabo preto (-) na bateria boa
4. Conecte a outra ponta do preto em um ponto de metal do motor (terra)
5. Dê partida no carro com bateria boa
6. Aguarde 2-3 minutos
7. Tente dar partida no carro com bateria fraca
8. Remova os cabos na ordem inversa

### Sinais de Bateria Fraca
- Partida lenta
- Luzes fracas
- Sistema elétrico falhando
- Bateria com mais de 3 anos
"""

FEATURES_GUIDE = """
# Manual de Recursos - GenAuto X1 2024

## Sistema Multimídia GenConnect 10"

### Conectividade
- **Android Auto**: Conecte seu celular Android via cabo USB
- **Apple CarPlay**: Conecte seu iPhone via cabo USB
- **Bluetooth**: Pareie até 8 dispositivos
- **Wi-Fi**: Hotspot integrado (requer plano de dados)

### Espelhamento de Tela
1. Conecte o cabo USB na porta do console central
2. Autorize a conexão no celular
3. O espelhamento iniciará automaticamente

### Comandos de Voz
Ative dizendo "Ok GenAuto" ou pressionando o botão no volante:
- "Ligar para [contato]"
- "Navegar para [endereço]"
- "Tocar [música/artista]"
- "Temperatura [graus]"

## Piloto Automático Adaptativo (ACC)

### Ativação
1. Acelere até a velocidade desejada (mínimo 30 km/h)
2. Pressione o botão SET no volante
3. Ajuste a distância do veículo à frente (3 níveis)
4. Para desativar: pressione o freio ou o botão OFF

### Limitações
- Não funciona abaixo de 30 km/h
- Curvas acentuadas podem desativar o sistema
- Chuva forte pode interferir nos sensores
- Sempre mantenha as mãos no volante

## Assistente de Estacionamento

### Como Usar
1. Acione a seta para o lado da vaga
2. Passe pela vaga em velocidade baixa (<20 km/h)
3. Quando aparecer "P" no painel, pare o veículo
4. Selecione a vaga detectada
5. Solte o volante e controle apenas os pedais
6. O sistema fará a manobra automaticamente

### Tipos de Vaga Suportados
- Paralela (baliza)
- Perpendicular (90°)
- Diagonal (45°)

## Sensores e Câmeras

### Sensor de Estacionamento
- 4 sensores dianteiros
- 4 sensores traseiros
- Alerta sonoro progressivo
- Visualização gráfica no multimídia

### Câmera de Ré
- Resolução HD
- Linhas de guia dinâmicas
- Sensor de movimento
- Ativa automaticamente ao engatar a ré

### Câmera 360°
- Visão superior do veículo
- 4 câmeras sincronizadas
- Útil para manobras em espaços apertados
"""

FAQ_CONTENT = """
# Perguntas Frequentes - GenAuto X1

## Garantia

**P: Qual o prazo de garantia do veículo?**
R: O GenAuto X1 possui garantia de 3 anos ou 100.000 km (o que ocorrer primeiro), válida para defeitos de fabricação.

**P: A garantia cobre desgaste natural?**
R: Não. Itens de desgaste como pastilhas de freio, pneus, palhetas e embreagem não são cobertos pela garantia.

**P: Posso fazer manutenção fora da concessionária sem perder a garantia?**
R: Sim, desde que utilize peças genuínas e siga o plano de manutenção do manual. Guarde todas as notas fiscais.

## Combustível

**P: Posso usar gasolina aditivada?**
R: Sim, gasolina aditivada pode ser usada e ajuda a manter o sistema de injeção limpo.

**P: Qual a diferença de desempenho entre gasolina e etanol?**
R: Com etanol, a potência é ligeiramente menor (116cv vs 128cv), mas o torque é similar. O consumo com etanol é aproximadamente 30% maior.

**P: O que acontece se eu misturar gasolina e etanol?**
R: Não há problema. O sistema flex se adapta automaticamente a qualquer proporção de mistura.

## Pneus

**P: Qual a pressão correta dos pneus?**
R: Dianteiros: 32 psi / Traseiros: 32 psi (com carga normal). Para carga máxima: 35 psi.

**P: Posso usar pneus de medidas diferentes?**
R: Não é recomendado. Use sempre a medida original (205/60 R16) para manter a segurança e não invalidar a garantia.

**P: O estepe é de uso temporário?**
R: Sim. O estepe temporário deve ser usado apenas em emergências, com velocidade máxima de 80 km/h e distância máxima de 80 km.

## Tecnologia

**P: Como atualizo o sistema multimídia?**
R: Atualizações são feitas automaticamente via Wi-Fi ou na concessionária durante as revisões.

**P: O carro tem rastreador?**
R: Sim, o GenAuto X1 possui rastreador integrado. Ative o serviço pelo app GenAuto Connect.

**P: Como funciona a chave presencial?**
R: Com a chave no bolso, aproxime-se do veículo para destravar automaticamente. Para dar partida, basta pressionar o botão Start/Stop com o pé no freio.

## Manutenção

**P: Com que frequência devo trocar o óleo?**
R: A cada 10.000 km ou 12 meses, o que ocorrer primeiro.

**P: Qual óleo devo usar?**
R: SAE 5W-30 com especificação API SN ou superior.

**P: A correia dentada precisa ser trocada?**
R: Sim, a cada 100.000 km ou conforme indicação do computador de bordo.
"""

SAFETY_GUIDE = """
# Manual de Segurança - GenAuto X1

## Equipamentos de Segurança

### Airbags
O veículo possui 6 airbags:
- 2 frontais (motorista e passageiro)
- 2 laterais (motorista e passageiro)
- 2 de cortina (proteção de cabeça)

**ATENÇÃO**: 
- Nunca instale cadeirinha infantil no banco dianteiro
- Crianças menores de 10 anos devem viajar no banco traseiro
- Não coloque objetos sobre o painel ou airbags

### Cintos de Segurança
- Todos os cintos são de 3 pontos com retrator
- Cintos dianteiros possuem pré-tensionador
- Alerta sonoro e visual para cintos desafivelados

### Sistemas de Assistência (ADAS)

**Frenagem Automática de Emergência (AEB)**
- Detecta obstáculos e pedestres
- Alerta o motorista
- Freia automaticamente se não houver reação
- Funciona entre 5-80 km/h

**Alerta de Colisão Frontal (FCW)**
- Monitora veículos à frente
- Alerta visual e sonoro
- Prepara o sistema de freios

**Assistente de Permanência em Faixa (LKA)**
- Detecta marcações na pista
- Alerta se sair da faixa sem sinalizar
- Pode corrigir levemente a direção

**Monitoramento de Ponto Cego (BSM)**
- Sensores nos retrovisores laterais
- Alerta visual quando há veículo no ponto cego
- Especialmente útil em mudanças de faixa

## Cadeirinha Infantil

### Fixação ISOFIX
O veículo possui pontos de ancoragem ISOFIX nos bancos traseiros laterais:
- 2 pontos de ancoragem inferior
- 1 ponto Top Tether (parte superior)

### Recomendação por Idade
- Até 1 ano: Bebê conforto voltado para trás
- 1-4 anos: Cadeirinha voltada para frente
- 4-7,5 anos: Assento de elevação com encosto
- 7,5-10 anos: Assento de elevação (booster)

## Em Caso de Acidente

### Procedimentos
1. Mantenha a calma
2. Ligue o pisca-alerta
3. Sinalize a via (triângulo a 30m do veículo)
4. Verifique se há feridos
5. Chame socorro: SAMU 192 / Bombeiros 193
6. Não mova feridos (exceto risco de incêndio)
7. Registre boletim de ocorrência

### Contatos de Emergência
- Assistência 24h GenAuto: 0800 XXX XXXX
- SAMU: 192
- Bombeiros: 193
- Polícia: 190
"""


DOCUMENTS = [
    {
        "text": VEHICLE_SPECS,
        "source": "especificacoes_genautox1_2024.md",
        "document_type": "spec",
    },
    {
        "text": MAINTENANCE_GUIDE,
        "source": "guia_manutencao_genautox1.md",
        "document_type": "manual",
    },
    {
        "text": TROUBLESHOOTING_GUIDE,
        "source": "guia_diagnostico_problemas.md",
        "document_type": "troubleshoot",
    },
    {
        "text": FEATURES_GUIDE,
        "source": "manual_recursos_genautox1.md",
        "document_type": "guide",
    },
    {
        "text": FAQ_CONTENT,
        "source": "faq_genautox1.md",
        "document_type": "faq",
    },
    {
        "text": SAFETY_GUIDE,
        "source": "manual_seguranca_genautox1.md",
        "document_type": "manual",
    },
]


async def seed_knowledge_base():
    """Seed the knowledge base with sample documentation."""
    print("🚗 GenAI Auto - Knowledge Base Seeder")
    print("=" * 50)

    async with async_session() as db:
        pipeline = RAGPipeline(db)

        # Check current stats
        stats = await pipeline.get_stats()
        print(f"\n📊 Current stats: {stats['total_chunks']} chunks, {stats['total_sources']} sources")

        if stats['total_chunks'] > 0:
            response = input("\n⚠️  Knowledge base already has data. Clear and reseed? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return

            # Clear existing data
            print("\n🗑️  Clearing existing data...")
            for doc in DOCUMENTS:
                await pipeline.delete_document(doc["source"])
            print("   Done!")

        print("\n📥 Ingesting documents...\n")

        total_chunks = 0
        total_tokens = 0

        for doc in DOCUMENTS:
            print(f"   📄 {doc['source']}...")
            
            result = await pipeline.ingest_text(
                text=doc["text"],
                source=doc["source"],
                document_type=doc["document_type"],
            )
            
            total_chunks += result["chunks_created"]
            total_tokens += result["tokens_used"]
            
            print(f"      ✅ {result['chunks_created']} chunks, {result['tokens_used']} tokens")

        print("\n" + "=" * 50)
        print(f"✨ Seeding complete!")
        print(f"   📚 Documents: {len(DOCUMENTS)}")
        print(f"   📦 Total chunks: {total_chunks}")
        print(f"   🎯 Total tokens: {total_tokens}")

        # Show final stats
        final_stats = await pipeline.get_stats()
        print(f"\n📊 Final stats: {final_stats}")


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
