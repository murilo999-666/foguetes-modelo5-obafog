"""Verificação final: abre cada .ork do disco (como o OpenRocket abre), confere se o motor
foi resolvido pelo banco de motores e roda de novo TODAS as simulações salvas."""
import os, sys, math
from pathlib import Path
from m5lib import Ctx, RAIZ, estabilidade_estatica

def main():
    c = Ctx.get(); b = c.b
    orks = sorted((RAIZ / "foguete1_obafog").glob("F1_*.ork")) + sorted((RAIZ / "foguete2_livre").glob("F2_*.ork"))
    falhas = 0
    for ork in orks:
        doc = b.load_document(str(ork))
        rocket = doc.getRocket()
        sims = list(doc.getSimulations())
        est = estabilidade_estatica(doc)
        print(f"\n== {ork.name}: {len(sims)} simulações | massa {est['massa_g']:.1f} g | margem {est['cal']:.2f} cal")
        for s in sims:
            try:
                fcid = s.getFlightConfigurationId()
                cfg = rocket.getFlightConfiguration(fcid)
                motores = [str(m.getMotor().getDesignation()) for m in cfg.getActiveMotors()]
                b.run_simulation(s)
                d = s.getSimulatedData()
                br = d.getBranch(0)
                X = br.get(c.FlightDataType.TYPE_POSITION_X); Y = br.get(c.FlightDataType.TYPE_POSITION_Y)
                dist = math.hypot(float(X.get(X.size()-1)), float(Y.get(Y.size()-1)))
                print(f"   ok  {str(s.getName())[:48]:48s} motor {motores} apogeu {float(d.getMaxAltitude()):6.1f} m  distância {dist:6.1f} m")
            except Exception as e:
                falhas += 1
                print(f"   FALHOU {s.getName()}: {e}")
    print(f"\nfalhas: {falhas}")

if __name__ == "__main__":
    main(); os._exit(0)
