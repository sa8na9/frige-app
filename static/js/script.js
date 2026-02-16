// =============================================
// 冷蔵庫管理アプリ JavaScript
// =============================================

// フラッシュメッセージの自動非表示(3秒後)
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 3000);
    });
});

// 削除確認ダイアログ(HTMLのonsubmitで使用)
function confirmDelete() {
    return confirm('本当に削除しますか?');
}

// キャンセル確認ダイアログ(HTMLのonclickで使用)
function confirmCancel() {
    const hasInput = document.querySelector('input[type="text"]').value.trim() !== '';
    if (hasInput) {
        return confirm('入力内容は破棄されます。よろしいですか?');
    }
    return true;
}