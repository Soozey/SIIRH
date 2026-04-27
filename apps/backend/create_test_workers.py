#!/usr/bin/env python3
"""
Script pour créer des salariés de test avec des données organisationnelles
"""

from sqlalchemy.orm import Session
from app.config.config import get_db, engine
from app.models import Worker, Employer
from datetime import date

def create_test_workers():
    """Crée des salariés de test avec différentes structures organisationnelles"""
    
    # Créer une session
    db = Session(bind=engine)
    
    try:
        # Vérifier qu'on a un employeur
        employer = db.query(Employer).first()
        if not employer:
            print("❌ Aucun employeur trouvé. Créez d'abord un employeur.")
            return False
        
        print(f"✅ Employeur trouvé : {employer.raison_sociale} (ID: {employer.id})")
        
        # Créer des salariés de test avec différentes structures
        test_workers = [
            {
                "matricule": "TEST001",
                "nom": "DUPONT",
                "prenom": "Jean",
                "etablissement": "Siège Social",
                "departement": "Ressources Humaines",
                "service": "Recrutement",
                "poste": "Responsable RH"
            },
            {
                "matricule": "TEST002", 
                "nom": "MARTIN",
                "prenom": "Marie",
                "etablissement": "Siège Social",
                "departement": "Ressources Humaines",
                "service": "Formation",
                "poste": "Formatrice"
            },
            {
                "matricule": "TEST003",
                "nom": "BERNARD",
                "prenom": "Pierre",
                "etablissement": "Siège Social",
                "departement": "Informatique",
                "service": "Développement",
                "poste": "Développeur"
            },
            {
                "matricule": "TEST004",
                "nom": "DURAND",
                "prenom": "Sophie",
                "etablissement": "Agence Nord",
                "departement": "Commercial",
                "service": "Ventes",
                "poste": "Commerciale"
            },
            {
                "matricule": "TEST005",
                "nom": "MOREAU",
                "prenom": "Luc",
                "etablissement": "Agence Sud",
                "departement": "Technique",
                "service": None,  # Pas de service
                "poste": "Technicien"
            }
        ]
        
        created_count = 0
        
        for worker_data in test_workers:
            # Vérifier si le salarié existe déjà
            existing = db.query(Worker).filter(Worker.matricule == worker_data["matricule"]).first()
            if existing:
                print(f"⚠️ Salarié {worker_data['matricule']} existe déjà, ignoré")
                continue
            
            # Créer le salarié
            worker = Worker(
                employer_id=employer.id,
                matricule=worker_data["matricule"],
                nom=worker_data["nom"],
                prenom=worker_data["prenom"],
                etablissement=worker_data["etablissement"],
                departement=worker_data["departement"],
                service=worker_data["service"],
                poste=worker_data["poste"],
                date_embauche=date.today(),
                salaire_base=2000000.0,  # 2M Ariary
                vhm=173.33
            )
            
            db.add(worker)
            created_count += 1
            print(f"✅ Salarié créé : {worker_data['matricule']} - {worker_data['nom']} {worker_data['prenom']}")
        
        db.commit()
        print(f"\n🎉 {created_count} salariés de test créés avec succès !")
        
        # Afficher un résumé
        total_workers = db.query(Worker).filter(Worker.employer_id == employer.id).count()
        print(f"📊 Total salariés pour {employer.raison_sociale} : {total_workers}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des salariés : {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("👥 Création de salariés de test pour l'organisation")
    print("=" * 50)
    
    success = create_test_workers()
    
    if success:
        print("\n📋 Prochaines étapes :")
        print("   1. Tester la migration organisationnelle")
        print("   2. Vérifier l'arbre organisationnel")
        print("   3. Tester l'assignation de salariés")
    else:
        print("\n❌ Création échouée !")