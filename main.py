import sys
from PyQt5.QtWidgets import QApplication
from model import SignalGeneratorModel
from view import SignalGeneratorView
from presenter import SignalGeneratorPresenter

def main():
    # 1. Initialisation de l'application Qt
    app = QApplication(sys.argv)

    NUM_OSCILLATORS = 10

    # 2. Instanciation du Modèle, de la Vue et du Présentateur
    model = SignalGeneratorModel(num_oscillators=NUM_OSCILLATORS)
    view = SignalGeneratorView(num_oscillators=NUM_OSCILLATORS)
    
    # ON GARDE UNE RÉFÉRENCE STRICTE AU PRÉSENTATEUR DANS UNE VARIABLE
    presenter = SignalGeneratorPresenter(model, view)

    # 3. Affichage de la fenêtre principale
    view.show()

    # 4. Nettoyage lors de la fermeture
    app.aboutToQuit.connect(model.stop)

    # 5. Lancement de la boucle d'événements principale (Empêche l'application de quitter)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()