window.hack_delay = async function(ms) {
    await new Promise(r => setTimeout(r, ms));
}

window.hack_injectcss = function(cssrule) {
    document.styleSheets[0].insertRule(`${cssrule}`, 0);
}

window.hack_hide_elems = function(selector) {
    let elems = document.querySelectorAll(selector);
    for (const elem of elems) {
        elem.style.display="none";
    }
}

window.hack_hide_elems_keep_first = function(selector) {
    let elems = document.querySelectorAll(selector);
    for (let i = 1; i < elems.length; i++) {
        elems[i].style.display="none";
    }
}

window.hack_click = function(el) {
    let click_event = new CustomEvent('click');
    el.dispatchEvent(click_event);
}
