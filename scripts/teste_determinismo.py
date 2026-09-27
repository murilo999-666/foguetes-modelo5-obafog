import os
from m5lib import Cenario, build_f1, simular
from otimizar_f1 import humano_ajustado
def main():
    h = humano_ajustado()
    doc, meta = build_f1(h)
    for turb in (0.0, 0.1):
        for seed in (7, 7, 8):
            rs = [simular(doc, meta, Cenario(motor="OBAFOG-M5_NEU_I05", vento=6.0, vento_de=180.0, turb=turb, seed=seed))["perp"] for _ in range(2)]
            print(f"turb {turb} seed {seed}: {[round(x,2) for x in rs]}", flush=True)
    # novo documento, mesma semente
    doc2, meta2 = build_f1(h)
    print("doc novo:", round(simular(doc2, meta2, Cenario(motor="OBAFOG-M5_NEU_I05", vento=6.0, vento_de=180.0, turb=0.1, seed=7))["perp"], 2))
if __name__ == "__main__":
    main(); os._exit(0)
