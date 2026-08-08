# Reporte de calidad -- Bronze a Silver

*Generado por `opa normalize`. 91 snapshots con corte declarado en el manifiesto.*

## Resumen

- Normalizados a parquet: **88**
- Omitidos por corrupción conocida en la fuente: **3**
- Con esquema desconocido (no en `conf/schema_map.yml`): **0**
- Con error de lectura: **0**

- Filas totales procesadas: 179,179
- Filas válidas escritas a parquet: 177,245 (98.9%)
- Filas en cuarentena (fallan el contrato Pandera, no se escriben): 1,934

## Omitidos por corrupción conocida en la fuente

Ver `conf/schema_map.yml` (`snapshots_conocidos_corruptos`) para el detalle de cada uno.

- `opa_2024_1_0923b83f.csv`
- `opa_2024_1_d9f08486.csv`
- `opa_2024_1_c38b00d6.csv`

## Detalle por snapshot normalizado

| snapshot_id | archivo | filas | válidas | rechazadas | fechas sin parsear |
|---|---|---|---|---|---|
| 2015_anual_cf606d2d | `opa_2015_anual_cf606d2d.csv` | 3140 | 3087 | 53 | 0 |
| 2016Q3_b33e65ed | `opa_2016_3_b33e65ed.xlsx` | 3616 | 3574 | 42 | 0 |
| 2016Q3_ccbf1d23 | `opa_2016_3_ccbf1d23.csv` | 3616 | 3574 | 42 | 0 |
| 2016_anual_094c386d | `opa_2016_anual_094c386d.csv` | 3909 | 3860 | 49 | 0 |
| 2016_anual_14f84d67 | `opa_2016_anual_14f84d67.csv` | 3181 | 3137 | 44 | 0 |
| 2016_anual_c762f4e4 | `opa_2016_anual_c762f4e4.csv` | 1426 | 1385 | 41 | 0 |
| 2016_anual_ccbf1d23 | `opa_2016_anual_ccbf1d23.csv` | 3616 | 3574 | 42 | 0 |
| 2016_anual_f5ed99d6 | `opa_2016_anual_f5ed99d6.xlsx` | 3909 | 3860 | 49 | 0 |
| 2017Q1_597aec7b | `opa_2017_1_597aec7b.xlsx` | 3293 | 3260 | 33 | 0 |
| 2017Q1_65831160 | `opa_2017_1_65831160.csv` | 3293 | 3260 | 33 | 0 |
| 2017Q2_4d1d7802 | `opa_2017_2_4d1d7802.csv` | 3470 | 3436 | 34 | 0 |
| 2017Q3_52ecf72a | `opa_2017_3_52ecf72a.csv` | 3593 | 3559 | 34 | 0 |
| 2017_anual_03dc3a21 | `opa_2017_anual_03dc3a21.csv` | 3810 | 3768 | 42 | 0 |
| 2017_anual_2da163ff | `opa_2017_anual_2da163ff.csv` | 3909 | 3859 | 50 | 0 |
| 2017_anual_4d1d7802 | `opa_2017_anual_4d1d7802.csv` | 3470 | 3436 | 34 | 0 |
| 2017_anual_597aec7b | `opa_2017_anual_597aec7b.xlsx` | 3293 | 3260 | 33 | 0 |
| 2017_anual_65831160 | `opa_2017_anual_65831160.csv` | 3293 | 3260 | 33 | 0 |
| 2018Q3_7046705c | `opa_2018_3_7046705c.xlsx` | 2537 | 2518 | 19 | 0 |
| 2018_anual_5424ac9b | `opa_2018_anual_5424ac9b.csv` | 3157 | 3125 | 32 | 0 |
| 2019Q1_b9d2c0b5 | `opa_2019_1_b9d2c0b5.csv` | 1513 | 1500 | 13 | 3 |
| 2019Q2_6fe6cab1 | `opa_2019_2_6fe6cab1.csv` | 1695 | 1682 | 13 | 6 |
| 2019Q3_0fc17d15 | `opa_2019_3_0fc17d15.csv` | 1863 | 1850 | 13 | 24 |
| 2019Q4_14f1d140 | `opa_2019_4_14f1d140.csv` | 1959 | 1945 | 14 | 32 |
| 2019_anual_545e6452 | `opa_2019_anual_545e6452.csv` | 2745 | 2475 | 270 | 24 |
| 2020Q1_17744cfe | `opa_2020_1_17744cfe.csv` | 494 | 494 | 0 | 0 |
| 2020Q2_32f61f30 | `opa_2020_2_32f61f30.csv` | 493 | 493 | 0 | 0 |
| 2020Q3_1c90993a | `opa_2020_3_1c90993a.csv` | 1549 | 1533 | 16 | 58 |
| 2020Q4_1c90993a | `opa_2020_4_1c90993a.csv` | 1549 | 1533 | 16 | 58 |
| 2020_anual_367bf0e8 | `opa_2020_anual_367bf0e8.csv` | 2355 | 2336 | 19 | 117 |
| 2021Q1_6d074e99 | `opa_2021_1_6d074e99.csv` | 595 | 594 | 1 | 0 |
| 2021Q2_93ccafb8 | `opa_2021_2_93ccafb8.csv` | 595 | 594 | 1 | 0 |
| 2021Q2_aa2202ee | `opa_2021_2_aa2202ee.csv` | 1974 | 1952 | 22 | 0 |
| 2021Q2_cc0fd97d | `opa_2021_2_cc0fd97d.csv` | 1314 | 1293 | 21 | 0 |
| 2021Q3_1aa148c6 | `opa_2021_3_1aa148c6.csv` | 595 | 594 | 1 | 25 |
| 2021Q3_883920d2 | `opa_2021_3_883920d2.csv` | 1540 | 1520 | 20 | 88 |
| 2021Q3_ae02c33e | `opa_2021_3_ae02c33e.csv` | 2265 | 2241 | 24 | 123 |
| 2021Q4_1d0d53f6 | `opa_2021_4_1d0d53f6.csv` | 1594 | 1575 | 19 | 98 |
| 2021Q4_2431dc5a | `opa_2021_4_2431dc5a.csv` | 2537 | 2513 | 24 | 153 |
| 2021Q4_341ad580 | `opa_2021_4_341ad580.csv` | 667 | 665 | 2 | 28 |
| 2021_anual_48a4c666 | `opa_2021_anual_48a4c666.csv` | 1786 | 1765 | 21 | 0 |
| 2022Q1_226a3eea | `opa_2022_1_226a3eea.csv` | 1149 | 1132 | 17 | 96 |
| 2022Q1_4c33c9da | `opa_2022_1_4c33c9da.csv` | 704 | 701 | 3 | 28 |
| 2022Q1_f834c66f | `opa_2022_1_f834c66f.csv` | 1893 | 1873 | 20 | 124 |
| 2022Q2_546e679e | `opa_2022_2_546e679e.csv` | 2217 | 2194 | 23 | 135 |
| 2022Q2_6e73e23e | `opa_2022_2_6e73e23e.csv` | 705 | 702 | 3 | 28 |
| 2022Q2_9bf16095 | `opa_2022_2_9bf16095.csv` | 1468 | 1448 | 20 | 107 |
| 2022Q3_63da403a | `opa_2022_3_63da403a.csv` | 2571 | 2548 | 23 | 159 |
| 2022Q3_d75b6a95 | `opa_2022_3_d75b6a95.csv` | 1733 | 1713 | 20 | 110 |
| 2022Q3_fe83e385 | `opa_2022_3_fe83e385.csv` | 703 | 700 | 3 | 28 |
| 2022Q4_7a4aaa41 | `opa_2022_4_7a4aaa41.csv` | 703 | 700 | 3 | 28 |
| 2022Q4_7e76c9a1 | `opa_2022_4_7e76c9a1.csv` | 2774 | 2751 | 23 | 168 |
| 2022Q4_f9c7c571 | `opa_2022_4_f9c7c571.csv` | 1859 | 1839 | 20 | 116 |
| 2023Q1_24844295 | `opa_2023_1_24844295.csv` | 1227 | 1211 | 16 | 105 |
| 2023Q1_cd1ea7a9 | `opa_2023_1_cd1ea7a9.csv` | 803 | 800 | 3 | 28 |
| 2023Q1_e93412d6 | `opa_2023_1_e93412d6.csv` | 2099 | 2080 | 19 | 133 |
| 2023Q2_3e606ad4 | `opa_2023_2_3e606ad4.csv` | 802 | 799 | 3 | 28 |
| 2023Q2_61ee341b | `opa_2023_2_61ee341b.csv` | 2520 | 2498 | 22 | 185 |
| 2023Q2_fbbab7a7 | `opa_2023_2_fbbab7a7.csv` | 1665 | 1646 | 19 | 157 |
| 2023Q3_3e82db6a | `opa_2023_3_3e82db6a.csv` | 802 | 799 | 3 | 28 |
| 2023Q3_8c34ee65 | `opa_2023_3_8c34ee65.csv` | 1990 | 1971 | 19 | 183 |
| 2023Q3_a4f4acf0 | `opa_2023_3_a4f4acf0.csv` | 2843 | 2821 | 22 | 211 |
| 2023Q4_2e5f0315 | `opa_2023_4_2e5f0315.csv` | 2121 | 2091 | 30 | 196 |
| 2023Q4_6b65707d | `opa_2023_4_6b65707d.csv` | 802 | 787 | 15 | 28 |
| 2023Q4_bacfc3da | `opa_2023_4_bacfc3da.csv` | 2981 | 2936 | 45 | 226 |
| 2024Q2_0de656ed | `opa_2024_2_0de656ed.csv` | 1751 | 1739 | 12 | 125 |
| 2024Q2_7825bc82 | `opa_2024_2_7825bc82.csv` | 919 | 915 | 4 | 37 |
| 2024Q2_dcf390ef | `opa_2024_2_dcf390ef.csv` | 2695 | 2679 | 16 | 165 |
| 2024Q3_338f4085 | `opa_2024_3_338f4085.csv` | 3011 | 2995 | 16 | 166 |
| 2024Q3_8e5fe3bc | `opa_2024_3_8e5fe3bc.csv` | 919 | 915 | 4 | 37 |
| 2024Q3_c53d1581 | `opa_2024_3_c53d1581.csv` | 1902 | 1890 | 12 | 119 |
| 2024Q4_61408863 | `opa_2024_4_61408863.csv` | 3110 | 3093 | 17 | 161 |
| 2024Q4_626f3d54 | `opa_2024_4_626f3d54.csv` | 1976 | 1963 | 13 | 114 |
| 2024Q4_c5a2cfc6 | `opa_2024_4_c5a2cfc6.csv` | 949 | 945 | 4 | 38 |
| 2025Q1_4f15d877 | `opa_2025_1_4f15d877.csv` | 2179 | 2167 | 12 | 104 |
| 2025Q1_a453a8a9 | `opa_2025_1_a453a8a9.csv` | 1184 | 1176 | 8 | 48 |
| 2025Q1_bdf31d45 | `opa_2025_1_bdf31d45.csv` | 994 | 990 | 4 | 56 |
| 2025Q2_7ccbee19 | `opa_2025_2_7ccbee19.csv` | 2697 | 2681 | 16 | 115 |
| 2025Q2_9c791a89 | `opa_2025_2_9c791a89.csv` | 994 | 990 | 4 | 56 |
| 2025Q2_a5085199 | `opa_2025_2_a5085199.csv` | 1694 | 1682 | 12 | 59 |
| 2025Q3_2c7651d0 | `opa_2025_3_2c7651d0.csv` | 2090 | 2076 | 14 | 69 |
| 2025Q3_948bb5ab | `opa_2025_3_948bb5ab.csv` | 3106 | 3088 | 18 | 125 |
| 2025Q3_ee36889b | `opa_2025_3_ee36889b.csv` | 994 | 990 | 4 | 56 |
| 2025Q4_14cfa99c | `opa_2025_4_14cfa99c.csv` | 2160 | 2145 | 15 | 76 |
| 2025Q4_200343ee | `opa_2025_4_200343ee.csv` | 3187 | 3161 | 26 | 132 |
| 2025Q4_dc23c5d8 | `opa_2025_4_dc23c5d8.csv` | 994 | 990 | 4 | 56 |
| 2026Q1_4b6fbd4e | `opa_2026_1_4b6fbd4e.csv` | 1620 | 1606 | 14 | 43 |
| 2026Q1_bcdb44ae | `opa_2026_1_bcdb44ae.csv` | 2666 | 2648 | 18 | 99 |
| 2026Q1_c21b577a | `opa_2026_1_c21b577a.csv` | 1046 | 1042 | 4 | 56 |

## Motivos de rechazo (filas en cuarentena)

- `opa_2015_anual_cf606d2d.csv`: str_matches('^[0-9A-Z]{10,11}$') (34), less_than_or_equal_to(-86.7) (19), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1)
- `opa_2016_anual_094c386d.csv`: less_than_or_equal_to(-86.7) (32), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (9), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2016_anual_f5ed99d6.xlsx`: less_than_or_equal_to(-86.7) (32), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (9), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2016_anual_ccbf1d23.csv`: less_than_or_equal_to(-86.7) (25), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2017_anual_03dc3a21.csv`: less_than_or_equal_to(-86.7) (17), str_matches('^[0-9A-Z]{10,11}$') (16), less_than_or_equal_to(32.8) (9), greater_than_or_equal_to(14.5) (6)
- `opa_2017_1_65831160.csv`: less_than_or_equal_to(-86.7) (18), str_matches('^[0-9A-Z]{10,11}$') (15), greater_than_or_equal_to(14.5) (8)
- `opa_2017_2_4d1d7802.csv`: less_than_or_equal_to(-86.7) (19), str_matches('^[0-9A-Z]{10,11}$') (15), greater_than_or_equal_to(14.5) (8)
- `opa_2017_3_52ecf72a.csv`: less_than_or_equal_to(-86.7) (18), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (8)
- `opa_2017_1_597aec7b.xlsx`: less_than_or_equal_to(-86.7) (18), str_matches('^[0-9A-Z]{10,11}$') (15), greater_than_or_equal_to(14.5) (8)
- `opa_2017_anual_2da163ff.csv`: less_than_or_equal_to(-86.7) (33), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (9), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2018_anual_5424ac9b.csv`: str_matches('^[0-9A-Z]{10,11}$') (15), less_than_or_equal_to(-86.7) (11), less_than_or_equal_to(32.8) (6), greater_than_or_equal_to(14.5) (1)
- `opa_2018_3_7046705c.xlsx`: str_matches('^[0-9A-Z]{10,11}$') (15), less_than_or_equal_to(-86.7) (4), greater_than_or_equal_to(14.5) (1)
- `opa_2019_anual_545e6452.csv`: not_nullable (248), str_matches('^[0-9A-Z]{10,11}$') (21), less_than_or_equal_to(-86.7) (2)
- `opa_2020_anual_367bf0e8.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (4), less_than_or_equal_to(32.8) (3), greater_than_or_equal_to(14.5) (1)
- `opa_2021_anual_48a4c666.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (4), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2021_2_aa2202ee.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (4), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2021_3_ae02c33e.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (3), greater_than_or_equal_to(14.5) (2), greater_than_or_equal_to(-118.5) (2)
- `opa_2021_4_2431dc5a.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (3), greater_than_or_equal_to(14.5) (2), greater_than_or_equal_to(-118.5) (2)
- `opa_2021_2_cc0fd97d.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(32.8) (4), less_than_or_equal_to(-86.7) (4), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2021_3_883920d2.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(32.8) (3), less_than_or_equal_to(-86.7) (3), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2021_4_1d0d53f6.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(32.8) (3), less_than_or_equal_to(-86.7) (3), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2021_2_93ccafb8.csv`: less_than_or_equal_to(-86.7) (1)
- `opa_2021_3_1aa148c6.csv`: less_than_or_equal_to(-86.7) (1)
- `opa_2021_4_341ad580.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), less_than_or_equal_to(-86.7) (1)
- `opa_2021_1_6d074e99.csv`: less_than_or_equal_to(-86.7) (1)
- `opa_2022_1_f834c66f.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (3), greater_than_or_equal_to(14.5) (2), less_than_or_equal_to(32.8) (2), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_2_546e679e.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (6), greater_than_or_equal_to(14.5) (2), less_than_or_equal_to(32.8) (2), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_3_63da403a.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (6), greater_than_or_equal_to(14.5) (2), less_than_or_equal_to(32.8) (2), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_4_7e76c9a1.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (6), greater_than_or_equal_to(14.5) (2), less_than_or_equal_to(32.8) (2), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_1_226a3eea.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(32.8) (2), less_than_or_equal_to(-86.7) (2), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_2_9bf16095.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (2), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_3_d75b6a95.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (2), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_4_f9c7c571.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (2), greater_than_or_equal_to(14.5) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2022_1_4c33c9da.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2022_2_6e73e23e.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2022_3_fe83e385.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2022_4_7a4aaa41.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2023_1_e93412d6.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (5), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1)
- `opa_2023_2_61ee341b.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (6), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1)
- `opa_2023_3_a4f4acf0.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (6), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1)
- `opa_2023_4_bacfc3da.csv`: str_matches('^[0-9A-Z]{10,11}$') (36), less_than_or_equal_to(-86.7) (6), less_than_or_equal_to(100) (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1)
- `opa_2023_1_24844295.csv`: str_matches('^[0-9A-Z]{10,11}$') (11), less_than_or_equal_to(-86.7) (4), less_than_or_equal_to(32.8) (1)
- `opa_2023_2_fbbab7a7.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (1)
- `opa_2023_3_8c34ee65.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(32.8) (1)
- `opa_2023_4_2e5f0315.csv`: str_matches('^[0-9A-Z]{10,11}$') (23), less_than_or_equal_to(-86.7) (5), less_than_or_equal_to(100) (1), less_than_or_equal_to(32.8) (1)
- `opa_2023_1_cd1ea7a9.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2023_2_3e606ad4.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2023_3_3e82db6a.csv`: str_matches('^[0-9A-Z]{10,11}$') (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2023_4_6b65707d.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2024_2_dcf390ef.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (3), greater_than_or_equal_to(14.5) (1)
- `opa_2024_3_338f4085.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (2), greater_than_or_equal_to(14.5) (1)
- `opa_2024_4_61408863.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (2), greater_than_or_equal_to(14.5) (1)
- `opa_2024_2_0de656ed.csv`: str_matches('^[0-9A-Z]{10,11}$') (10), less_than_or_equal_to(-86.7) (2)
- `opa_2024_3_c53d1581.csv`: str_matches('^[0-9A-Z]{10,11}$') (11), less_than_or_equal_to(-86.7) (1)
- `opa_2024_4_626f3d54.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (1)
- `opa_2024_2_7825bc82.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2024_3_8e5fe3bc.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2024_4_c5a2cfc6.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2025_1_4f15d877.csv`: str_matches('^[0-9A-Z]{10,11}$') (10), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2025_2_7ccbee19.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2025_3_948bb5ab.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(-86.7) (3), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1)
- `opa_2025_4_200343ee.csv`: str_matches('^[0-9A-Z]{10,11}$') (21), less_than_or_equal_to(-86.7) (3), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2025_1_a453a8a9.csv`: str_matches('^[0-9A-Z]{10,11}$') (8)
- `opa_2025_2_a5085199.csv`: str_matches('^[0-9A-Z]{10,11}$') (12)
- `opa_2025_3_2c7651d0.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (2), less_than_or_equal_to(32.8) (1)
- `opa_2025_4_14cfa99c.csv`: str_matches('^[0-9A-Z]{10,11}$') (12), less_than_or_equal_to(-86.7) (2), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2025_1_bdf31d45.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2025_2_9c791a89.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2025_3_ee36889b.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2025_4_dc23c5d8.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2026_1_bcdb44ae.csv`: str_matches('^[0-9A-Z]{10,11}$') (13), less_than_or_equal_to(-86.7) (3), greater_than_or_equal_to(0) (1), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1)
- `opa_2026_1_4b6fbd4e.csv`: str_matches('^[0-9A-Z]{10,11}$') (11), less_than_or_equal_to(-86.7) (2), greater_than_or_equal_to(0) (1), less_than_or_equal_to(32.8) (1)
- `opa_2026_1_c21b577a.csv`: str_matches('^[0-9A-Z]{10,11}$') (2), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(-86.7) (1)
- `opa_2016_3_ccbf1d23.csv`: less_than_or_equal_to(-86.7) (25), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2016_3_b33e65ed.xlsx`: less_than_or_equal_to(-86.7) (25), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (1), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2017_anual_65831160.csv`: less_than_or_equal_to(-86.7) (18), str_matches('^[0-9A-Z]{10,11}$') (15), greater_than_or_equal_to(14.5) (8)
- `opa_2017_anual_4d1d7802.csv`: less_than_or_equal_to(-86.7) (19), str_matches('^[0-9A-Z]{10,11}$') (15), greater_than_or_equal_to(14.5) (8)
- `opa_2017_anual_597aec7b.xlsx`: less_than_or_equal_to(-86.7) (18), str_matches('^[0-9A-Z]{10,11}$') (15), greater_than_or_equal_to(14.5) (8)
- `opa_2016_anual_c762f4e4.csv`: str_matches('^[0-9A-Z]{10,11}$') (26), less_than_or_equal_to(-86.7) (15), greater_than_or_equal_to(14.5) (1)
- `opa_2016_anual_14f84d67.csv`: less_than_or_equal_to(-86.7) (27), str_matches('^[0-9A-Z]{10,11}$') (16), greater_than_or_equal_to(14.5) (2), less_than_or_equal_to(32.8) (1), greater_than_or_equal_to(-118.5) (1)
- `opa_2019_2_6fe6cab1.csv`: str_matches('^[0-9A-Z]{10,11}$') (13)
- `opa_2019_3_0fc17d15.csv`: str_matches('^[0-9A-Z]{10,11}$') (13)
- `opa_2019_4_14f1d140.csv`: str_matches('^[0-9A-Z]{10,11}$') (14)
- `opa_2020_3_1c90993a.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(32.8) (2), less_than_or_equal_to(-86.7) (2)
- `opa_2020_4_1c90993a.csv`: str_matches('^[0-9A-Z]{10,11}$') (14), less_than_or_equal_to(32.8) (2), less_than_or_equal_to(-86.7) (2)
- `opa_2019_1_b9d2c0b5.csv`: str_matches('^[0-9A-Z]{10,11}$') (13)

