// =============================================
// 在庫管理アプリ JavaScript
// =============================================


// =============================================
// トースト通知（全画面共通）
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach((toast, index) => {
        setTimeout(() => toast.classList.add('show'), index * 100);
        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 300);
        }, 3000 + (index * 100));
    });
});


// =============================================
// 削除・キャンセル確認ダイアログ（全画面共通）
// =============================================
function confirmDelete() {
    return confirm('本当に削除しますか?');
}

function confirmCancel() {
    const input = document.querySelector('input[type="text"]');
    if (input && input.value.trim() !== '') {
        return confirm('入力内容は破棄されます。よろしいですか?');
    }
    return true;
}


// =============================================
// 文字数カウンター（フォームページ共通）
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    [
        ['name',       'charCount'],
        ['store_name', 'nameCount'],
        ['item_name',  'nameCount'],
        ['memo',       'memoCount'],
    ].forEach(([inputId, counterId]) => {
        const input   = document.getElementById(inputId);
        const counter = document.getElementById(counterId);
        if (input && counter) {
            input.addEventListener('input', () => {
                counter.textContent = input.value.length;
            });
        }
    });
});


// =============================================
// 日付パース（YYYY-MM-DD → ローカル時間のDateオブジェクト）
// =============================================
function parseLocalDate(value) {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day);
}


// =============================================
// 日付バリデーション（在庫登録・編集ページ）
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    const expiryDate   = document.getElementById('expiry_date');
    const openedDate   = document.getElementById('opened_date');
    const expiryWarning = document.getElementById('expiryWarning');
    const openedWarning = document.getElementById('openedWarning');

    if (!expiryDate || !openedDate) return;

    function validateDates() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        if (expiryDate.value) {
            const expiry = parseLocalDate(expiryDate.value);
            expiryWarning.style.display = expiry < today ? 'block' : 'none';
        } else {
            expiryWarning.style.display = 'none';
        }

        if (openedDate.value) {
            const opened = parseLocalDate(openedDate.value);
            openedWarning.style.display = opened > today ? 'block' : 'none';
        } else {
            openedWarning.style.display = 'none';
        }
    }

    validateDates();
    expiryDate.addEventListener('change', validateDates);
    openedDate.addEventListener('change', validateDates);
});


// =============================================
// 店舗作成: パスワード一致確認
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('createStoreForm');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        const password = document.getElementById('password').value;
        const confirm  = document.getElementById('password_confirm').value;
        if (password !== confirm) {
            e.preventDefault();
            alert('パスワードが一致しません');
        }
    });
});


// =============================================
// 店舗設定: 削除確認モーダル
// =============================================
function showDeleteConfirm() {
    const modal    = document.getElementById('deleteModal');
    const backdrop = document.getElementById('deleteBackdrop');
    if (modal)    modal.classList.add('show');
    if (backdrop) backdrop.classList.add('show');
}

function hideDeleteConfirm() {
    const modal    = document.getElementById('deleteModal');
    const backdrop = document.getElementById('deleteBackdrop');
    if (modal)    modal.classList.remove('show');
    if (backdrop) backdrop.classList.remove('show');
}

document.addEventListener('DOMContentLoaded', () => {
    const backdrop = document.getElementById('deleteBackdrop');
    if (backdrop) backdrop.addEventListener('click', hideDeleteConfirm);
});


// =============================================
// 在庫一覧: カテゴリ変更
// =============================================
function changeCategory(categoryId) {
    const select      = document.getElementById('categorySelect');
    const baseUrl     = select.dataset.baseUrl;
    const currentSort = select.dataset.currentSort;
    window.location.href = baseUrl + '?category=' + categoryId + '&sort=' + currentSort;
}


// =============================================
// 在庫一覧: カテゴリ管理モーダル
// =============================================
function showCategoryModal() {
    document.getElementById('categoryModal').style.display = 'block';
    document.getElementById('modalBackdrop').style.display = 'block';
}

function closeCategoryModal() {
    document.getElementById('categoryModal').style.display = 'none';
    document.getElementById('modalBackdrop').style.display = 'none';
}


// =============================================
// 在庫一覧: カテゴリ名インライン編集
// =============================================
function showCatEdit(id, name) {
    document.getElementById('cat-name-' + id).style.display = 'none';
    document.getElementById('cat-btns-' + id).style.display = 'none';
    const form = document.getElementById('cat-form-' + id);
    form.style.display = 'flex';
    const input = document.getElementById('cat-input-' + id);
    input.value = name;
    input.focus();
    input.select();
}

function hideCatEdit(id) {
    document.getElementById('cat-name-' + id).style.display = '';
    document.getElementById('cat-btns-' + id).style.display = '';
    document.getElementById('cat-form-' + id).style.display = 'none';
}


// =============================================
// 在庫一覧: 詳細表示トグル
// =============================================
function toggleDetail() {
    const details  = document.querySelectorAll('.item-details');
    const btn      = document.getElementById('toggleDetailBtn');
    const isHidden = localStorage.getItem('hideDetails') === 'true';

    if (isHidden) {
        details.forEach(el => el.style.display = '');
        btn.textContent = '詳細を非表示';
        btn.classList.remove('active');
        localStorage.setItem('hideDetails', 'false');
    } else {
        details.forEach(el => el.style.display = 'none');
        btn.textContent = '詳細を表示';
        btn.classList.add('active');
        localStorage.setItem('hideDetails', 'true');
    }
}


// =============================================
// 在庫一覧: 詳細表示状態の復元・スクロール位置管理
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    // 詳細表示の状態を復元
    const btn = document.getElementById('toggleDetailBtn');
    if (btn && localStorage.getItem('hideDetails') === 'true') {
        document.querySelectorAll('.item-details').forEach(el => el.style.display = 'none');
        btn.textContent = '詳細を表示';
        btn.classList.add('active');
    }

    // スクロール位置を復元
    const scrollPos = sessionStorage.getItem('scrollPos');
    if (scrollPos) {
        window.scrollTo(0, parseInt(scrollPos));
        sessionStorage.removeItem('scrollPos');
    }

    // 残量ボタンクリック時にスクロール位置を保存
    document.querySelectorAll('.qty-btn').forEach(qtyBtn => {
        qtyBtn.addEventListener('click', () => {
            sessionStorage.setItem('scrollPos', window.scrollY);
        });
    });
});
