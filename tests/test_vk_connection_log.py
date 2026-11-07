"""Проверка соединения с ВК обязана говорить правду: отказ не выглядит как успех.

`call_vk` возвращает полезную нагрузку как есть, и при отказе это `{"error": {...}}`.
Прежняя проверка брала из ответа имя группы, а при пустом ответе подставляла заглушку
и печатала «Connected to VK Group: …» — сборка отчитывалась об успешном соединении,
которого не было. Токен привязан к IP (код 5), и владелец об этом не узнавал.
"""

import importlib
import sys

import pytest


@pytest.fixture
def bfa():
    """Сборочный модуль офлайн: секрет подменён пустым, проверка при импорте не идёт в сеть."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("portal.env_file.secret", lambda name, path=None: "")
        patch.delitem(sys.modules, "build_final_analytics", raising=False)
        yield importlib.import_module("build_final_analytics")


def test_отказ_вика_печатается_как_отказ(bfa, monkeypatch, capsys):
    monkeypatch.setattr(bfa, "VK_API_TOKEN", "тестовый-токен")
    monkeypatch.setattr(bfa, "call_vk", lambda method, params: {
        "error": {"error_code": 5, "error_msg": "access_token was given to another ip address"}})
    bfa.verify_vk_connection()
    out = capsys.readouterr().out
    assert "Connected" not in out
    assert "код 5" in out
    assert "тестовый-токен" not in out, "токен не должен попадать в лог"


def test_пустой_ответ_не_выдаётся_за_соединение(bfa, monkeypatch, capsys):
    monkeypatch.setattr(bfa, "VK_API_TOKEN", "тестовый-токен")
    monkeypatch.setattr(bfa, "call_vk", lambda method, params: {})
    bfa.verify_vk_connection()
    out = capsys.readouterr().out
    assert "Connected" not in out
    assert "не подтверждено" in out


def test_настоящий_ответ_печатает_имя_группы(bfa, monkeypatch, capsys):
    monkeypatch.setattr(bfa, "VK_API_TOKEN", "тестовый-токен")
    monkeypatch.setattr(bfa, "call_vk", lambda method, params: {
        "response": {"groups": [{"name": "NEKKETSU SPORTS TOURNAMENTS"}]}})
    bfa.verify_vk_connection()
    out = capsys.readouterr().out
    assert "Connected to VK Group: NEKKETSU SPORTS TOURNAMENTS" in out


def test_без_токена_проверка_молчит_и_не_ходит_в_сеть(bfa, monkeypatch, capsys):
    monkeypatch.setattr(bfa, "VK_API_TOKEN", "")

    def forbidden(method, params):
        raise AssertionError("без токена запроса быть не должно")

    monkeypatch.setattr(bfa, "call_vk", forbidden)
    bfa.verify_vk_connection()
    assert "skipping" in capsys.readouterr().out