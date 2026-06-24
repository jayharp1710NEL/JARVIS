from app.memory.schemas import MemoryCreate, MemoryType, MemoryUpdate
from app.memory.service import memory_service


def test_save_and_get():
    item = memory_service.save(MemoryCreate(content="User likes dark mode", type=MemoryType.user_preference, tags=["ui"]))
    fetched = memory_service.get(item.id)
    assert fetched is not None
    assert fetched.content == "User likes dark mode"
    assert "ui" in fetched.tags


def test_search_keyword_and_tag():
    memory_service.save(MemoryCreate(content="Prefers Python and Rust", tags=["languages"]))
    memory_service.save(MemoryCreate(content="Lives in Toronto", tags=["location"]))
    res = memory_service.search("python language")
    assert res
    assert "Python" in res[0].item.content


def test_update_and_delete():
    item = memory_service.save(MemoryCreate(content="temp note"))
    updated = memory_service.update(item.id, MemoryUpdate(content="updated note", importance=0.9))
    assert updated.content == "updated note"
    assert updated.importance == 0.9
    assert memory_service.delete(item.id) is True
    assert memory_service.get(item.id) is None


def test_list_and_wipe():
    for i in range(3):
        memory_service.save(MemoryCreate(content=f"note {i}"))
    assert len(memory_service.list()) == 3
    n = memory_service.wipe_all()
    assert n == 3
    assert memory_service.list() == []
