(() => {
    const source = document.getElementById('course-content');
    const editor = document.getElementById('course-editor');
    if (!source || !editor) return;
    const canvas = editor.querySelector('[contenteditable]');
    const status = document.getElementById('course-editor-status');
    const file = document.getElementById('course-image');
    let selection;
    canvas.innerHTML = source.value;
    source.hidden = true;
    editor.hidden = false;
    const sync = () => { source.value = canvas.innerHTML; };
    document.addEventListener('selectionchange', () => {
        const selected = window.getSelection();
        if (selected.rangeCount && canvas.contains(selected.anchorNode)) selection = selected.getRangeAt(0).cloneRange();
    });
    function insert(command, value) {
        canvas.focus();
        if (selection) {
            const selected = window.getSelection();
            selected.removeAllRanges();
            selected.addRange(selection);
        }
        document.execCommand(command, false, value || null);
        sync();
    }
    editor.querySelectorAll('[data-cmd]').forEach(button => {
        button.addEventListener('mousedown', event => event.preventDefault());
        button.addEventListener('click', () => insert(button.dataset.cmd, button.dataset.value));
    });
    document.getElementById('course-add-link').onclick = () => {
        const url = window.prompt('Link URL (https://...)');
        if (url && /^https?:\/\//i.test(url)) insert('createLink', url);
    };
    document.getElementById('course-add-image').onclick = () => file.click();
    file.onchange = async () => {
        if (!file.files[0]) return;
        const data = new FormData();
        data.append('image', file.files[0]);
        status.textContent = 'Uploading image…';
        try {
            const response = await fetch('/courses/content-image', {method: 'POST', body: data});
            if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Please sign in again to upload images.');
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Upload failed.');
            insert('insertImage', result.url);
            status.textContent = 'Image added. Save the lesson to publish your changes.';
        } catch (error) { status.textContent = error.message; }
        file.value = '';
    };
    document.getElementById('course-add-video').onclick = () => {
        const value = window.prompt('YouTube video URL or video ID');
        if (!value) return;
        let code = value.trim();
        try {
            const url = new URL(code);
            if (['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(url.hostname)) code = url.searchParams.get('v') || url.pathname.split('/').pop();
            else if (url.hostname === 'youtu.be') code = url.pathname.slice(1);
            else code = '';
        } catch (_) { /* Bare video IDs are supported. */ }
        if (!/^[A-Za-z0-9_-]{11}$/.test(code || '')) {
            status.textContent = 'Enter a valid YouTube URL or video ID.';
            return;
        }
        insert('insertHTML', '<p><iframe src="https://www.youtube.com/embed/' + code + '" title="Course video" allowfullscreen></iframe></p><p><br></p>');
    };
    canvas.addEventListener('input', sync);
    source.form.addEventListener('submit', sync);
})();
