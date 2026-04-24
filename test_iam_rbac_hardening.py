import unittest
from datetime import date
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.config.config import Base
from app.routers.auth import update_iam_role_activation
from fastapi import HTTPException
from app.security import (
    build_user_access_profile_for_user,
    can_access_worker,
    get_user_active_role_codes,
    has_module_access_for_user,
    require_roles,
    seed_iam_catalog,
    user_has_any_role,
)


class IamRbacHardeningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.employer = models.Employer(raison_sociale="Karibo Services")
        self.db.add(self.employer)
        self.db.flush()

        self.unit_a = models.OrganizationalUnit(
            employer_id=self.employer.id,
            level="service",
            level_order=3,
            code="SVC-A",
            name="Service A",
        )
        self.unit_b = models.OrganizationalUnit(
            employer_id=self.employer.id,
            level="service",
            level_order=3,
            code="SVC-B",
            name="Service B",
        )
        self.db.add_all([self.unit_a, self.unit_b])
        self.db.flush()

        self.worker_manager = models.Worker(
            employer_id=self.employer.id,
            matricule="MGR001",
            nom="Manager",
            prenom="Alpha",
            organizational_unit_id=self.unit_a.id,
            date_embauche=date(2025, 1, 1),
            salaire_base=1200000,
        )
        self.worker_a = models.Worker(
            employer_id=self.employer.id,
            matricule="EMP001",
            nom="Employe",
            prenom="A",
            organizational_unit_id=self.unit_a.id,
            date_embauche=date(2025, 1, 1),
            salaire_base=800000,
        )
        self.worker_b = models.Worker(
            employer_id=self.employer.id,
            matricule="EMP002",
            nom="Employe",
            prenom="B",
            organizational_unit_id=self.unit_b.id,
            date_embauche=date(2025, 1, 1),
            salaire_base=850000,
        )
        self.db.add_all([self.worker_manager, self.worker_a, self.worker_b])
        self.db.flush()

        self.employee_user = models.AppUser(
            username="employee",
            password_hash="hash",
            role_code="employe",
            employer_id=self.employer.id,
            worker_id=self.worker_a.id,
        )
        self.manager_user = models.AppUser(
            username="manager",
            password_hash="hash",
            role_code="manager",
            employer_id=self.employer.id,
            worker_id=self.worker_manager.id,
        )
        self.composite_user = models.AppUser(
            username="assistant",
            password_hash="hash",
            role_code="employe",
            employer_id=self.employer.id,
            worker_id=self.worker_a.id,
        )
        self.rh_user = models.AppUser(
            username="rh_user",
            password_hash="hash",
            role_code="rh",
            employer_id=self.employer.id,
        )
        self.direction_readonly_user = models.AppUser(
            username="direction_ro",
            password_hash="hash",
            role_code="utilisateur_lecture_seule_direction",
            employer_id=self.employer.id,
        )
        self.plain_employeur_user = models.AppUser(
            username="plain_employeur",
            password_hash="hash",
            role_code="employeur",
            employer_id=self.employer.id,
        )
        self.delegated_admin_user = models.AppUser(
            username="delegated_admin",
            password_hash="hash",
            role_code="employeur",
            employer_id=self.employer.id,
        )
        self.db.add_all(
            [
                self.employee_user,
                self.manager_user,
                self.composite_user,
                self.rh_user,
                self.direction_readonly_user,
                self.plain_employeur_user,
                self.delegated_admin_user,
            ]
        )
        self.db.flush()

        seed_iam_catalog(self.db)

        self.db.add(
            models.IamUserRole(
                user_id=self.composite_user.id,
                role_code="assistante_rh",
                employer_id=self.employer.id,
                is_active=True,
            )
        )
        self.db.add(
            models.IamUserRole(
                user_id=self.delegated_admin_user.id,
                role_code="admin",
                is_active=True,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_multi_role_union_grants_expected_permissions(self):
        profile = build_user_access_profile_for_user(self.db, self.composite_user)
        self.assertIn("assistante_rh", profile["assigned_role_codes"])
        self.assertIn("master_data", profile["module_permissions"])
        self.assertIn("admin", profile["module_permissions"]["master_data"])
        self.assertTrue(user_has_any_role(self.db, self.composite_user, "rh"))
        self.assertTrue(has_module_access_for_user(self.db, self.composite_user, "payroll", "write"))

    def test_disabled_role_is_removed_from_effective_roles(self):
        activation = (
            self.db.query(models.IamRoleActivation)
            .filter(
                models.IamRoleActivation.scope_key == "installation",
                models.IamRoleActivation.role_code == "assistante_rh",
            )
            .first()
        )
        activation.is_enabled = False
        self.db.commit()

        active_roles = get_user_active_role_codes(self.db, self.composite_user)
        self.assertNotIn("assistante_rh", active_roles)
        self.assertFalse(user_has_any_role(self.db, self.composite_user, "rh"))
        self.assertFalse(has_module_access_for_user(self.db, self.composite_user, "master_data", "admin"))

    def test_direction_read_only_profile_cannot_write_payroll(self):
        self.assertTrue(has_module_access_for_user(self.db, self.direction_readonly_user, "payroll", "read"))
        self.assertFalse(has_module_access_for_user(self.db, self.direction_readonly_user, "payroll", "write"))
        self.assertFalse(has_module_access_for_user(self.db, self.direction_readonly_user, "master_data", "admin"))

    def test_employee_scope_is_self_only(self):
        self.assertTrue(can_access_worker(self.db, self.employee_user, self.worker_a))
        self.assertFalse(can_access_worker(self.db, self.employee_user, self.worker_b))

    def test_manager_scope_is_limited_to_its_organizational_unit(self):
        self.assertTrue(can_access_worker(self.db, self.manager_user, self.worker_a))
        self.assertFalse(can_access_worker(self.db, self.manager_user, self.worker_b))

    def test_delegated_admin_role_can_manage_installation_role_activation(self):
        response = update_iam_role_activation(
            role_code="manager",
            payload=schemas.IamRoleActivationUpdateIn(is_enabled=False),
            db=self.db,
            user=self.delegated_admin_user,
        )
        self.assertFalse(response.is_enabled)

        activation = (
            self.db.query(models.IamRoleActivation)
            .filter(
                models.IamRoleActivation.scope_key == "installation",
                models.IamRoleActivation.role_code == "manager",
            )
            .first()
        )
        self.assertIsNotNone(activation)
        self.assertFalse(activation.is_enabled)
        self.assertEqual(activation.updated_by_user_id, self.delegated_admin_user.id)

        manager_roles = get_user_active_role_codes(self.db, self.manager_user)
        self.assertNotIn("manager", manager_roles)

    def test_require_roles_blocks_write_when_module_permission_removed(self):
        self.db.query(models.IamRolePermission).filter(
            models.IamRolePermission.role_code == "rh",
            models.IamRolePermission.permission_code.like("payroll:%"),
        ).delete(synchronize_session=False)
        self.db.add(
            models.IamRolePermission(
                role_code="rh",
                permission_code="payroll:read",
                is_granted=True,
            )
        )
        self.db.commit()

        dependency = require_roles("admin", "rh", "employeur", "comptable")

        read_request = SimpleNamespace(url=SimpleNamespace(path="/payroll/runs"), method="GET")
        resolved_user = dependency(user=self.rh_user, db=self.db, request=read_request)
        self.assertEqual(resolved_user.id, self.rh_user.id)

        write_request = SimpleNamespace(url=SimpleNamespace(path="/payroll/get-or-create-run"), method="POST")
        with self.assertRaises(HTTPException) as ctx:
            dependency(user=self.rh_user, db=self.db, request=write_request)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_require_roles_blocks_user_admin_route_without_master_data_admin(self):
        self.db.query(models.IamRolePermission).filter(
            models.IamRolePermission.role_code == "employeur",
            models.IamRolePermission.permission_code.like("master_data:%"),
        ).delete(synchronize_session=False)
        self.db.add(
            models.IamRolePermission(
                role_code="employeur",
                permission_code="master_data:read",
                is_granted=True,
            )
        )
        self.db.commit()

        dependency = require_roles("admin", "rh", "employeur")
        request = SimpleNamespace(url=SimpleNamespace(path="/auth/users"), method="GET")
        with self.assertRaises(HTTPException) as ctx:
            dependency(user=self.plain_employeur_user, db=self.db, request=request)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
