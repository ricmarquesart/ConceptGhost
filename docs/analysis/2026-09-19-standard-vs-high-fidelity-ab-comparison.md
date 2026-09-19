# ConceptGhost v0.30 — A/B Standard vs High Fidelity

## Runs comparados
- Standard: `20260919T001109_789562Z_4c2675ab`
- High Fidelity: `20260919T002220_779479Z_222fcaea`

## Síntese
A comparação usa a mesma referência/câmera. A diferença principal é o profile de geometria.

### Julgamento visual
O High Fidelity é claramente superior como geometria de referência para o artista quando a câmera sai da vista original. Ele preserva melhor silhuetas de telhados, volumes e quinas de fachadas, torre central, arcos, portas e janelas, balcões, corrimãos, luminárias, escadas e pequenos ressaltos.

O Standard é mais liso e leve, mas perde separação e tende a transformar regiões arquitetônicas em camadas/slabs simplificadas.

Limitações observadas no High Fidelity:
- vegetação e ornamentos ficam mais ruidosos;
- regiões ambíguas de céu/nuvens continuam gerando superfícies facetadas;
- o ganho de detalhe aumenta muito o custo de memória/arquivo;
- continua sendo reconstrução single-view/2.5D, não cena 3D completa.

## Métricas principais

| Métrica | Standard | High Fidelity |
|---|---:|---:|
| Modelo | MoGe-3 ViT-L | MoGe-3 ViT-G |
| Refine steps | 3 | 7 |
| Stride | 3 | 1 |
| Vértices finais | 158,682 | 1,426,735 |
| Faces finais | 313,524 | 2,823,599 |
| Retenção RAW → mesh | 11.11% | 99.52% |
| RAW valid points | 1,428,291 | 1,433,610 |
| Depth-edge rejections | 0 (policy off) | 36,019 |
| Forbidden depth bridges | n/a | 0 |
| Reprojection RMSE | 0.707124 px | 0.707124 px |
| Camera-away faces | 0 | 0 |
| Opposed normals | 0 | 0 |
| FBX | 19.58 MB | 140.69 MB |
| Maya .ma | 68.20 MB | 638.88 MB |
| PrimaryMesh NPZ | 14.91 MB | 157.67 MB |

## Similaridade global e diferenças locais
Após ajuste afim da profundidade:
- R² ≈ 0.99615
- diferença relativa mediana ≈ 1.42%
- p95 ≈ 5.21%
- ~6.13% dos pixels comuns diferem >5%
- ~0.71% diferem >10%

O layout global permanece consistente, mas o High Fidelity altera de modo relevante as regiões locais onde os detalhes arquitetônicos aparecem.

## Proxy de alinhamento visual com a referência
Não é ground truth 3D; é apenas um proxy usando gradientes da imagem.
- correlação gradiente de profundidade × imagem: Standard ≈ 0.119; HF ≈ 0.389
- top 5% depth edges coincidindo com top 10% image edges: Standard ≈ 20.8%; HF ≈ 26.0%
- correlação de variação de normals × imagem: Standard ≈ 0.074; HF ≈ 0.151

## Conclusão
Para o objetivo do ConceptGhost — servir de ghost espacial no Maya — o High Fidelity entrega uma geometria significativamente mais útil e convincente fora da câmera original. O Standard continua útil como modo leve/rápido, mas sacrifica informação exatamente nas regiões que um artista precisa ler como volume.

A próxima melhoria visual mais valiosa não parece ser simplesmente aumentar ainda mais densidade. O maior ganho potencial está em tratar melhor regiões ambíguas como céu/nuvens, vegetação e superfícies muito finas, reduzindo ruído sem destruir bordas arquitetônicas.
