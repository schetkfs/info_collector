function deleteUser(userId) {
    if (!confirm('确定要删除该用户数据吗？此操作不可恢复！')) return;
    fetch('/admin/delete_user', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: userId})
    }).then(res => res.json()).then(resp => {
        if (resp.success) {
            alert('删除成功');
            window.location.reload();
        } else {
            alert(resp.msg || '删除失败');
        }
    }).catch(() => {
        alert('网络错误，删除失败');
    });
}
