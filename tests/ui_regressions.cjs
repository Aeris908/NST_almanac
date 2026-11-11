// Проверяет настоящие функции маршрутизации без сети и изменения базы.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('soccer.js', 'utf8');
const active = new Set(['tab-leaderboard']);
const sections = ['leaderboard','seasons','players','teams','special','h2h','clutch'].map(id => ({
  id: 'tab-'+id,
  classList: {toggle(_, on) {on ? active.add('tab-'+id) : active.delete('tab-'+id);}}
}));
const notices = {};
const context = {
  DATA: {profiles: [], seasons: [{id:'4'},{id:'6'}],team_tournaments:[{id:'team_1'}],special_tournaments:[{id:'cup_1'}]},
  URLSearchParams,
  window: {location:{hash:'#/bad'}},
  document: {
    querySelectorAll: q => q === '.view-content' ? sections : [],
    getElementById: id => id === 'playerModal' ? {classList:{contains:()=>false}} : notices[id],
    createElement: () => ({setAttribute(){}}),
    querySelector: () => ({prepend(el){notices[el.id]=el;}})
  },
  history: {
    replaceState(_,__,hash){context.window.location.hash=hash;},
    pushState(_,__,hash){context.window.location.hash=hash;}
  },
  setTimeout(){},
  selectedSeasonId:'6', seasonSubTab:'matches', teamSubTab:'matches', specialSubTab:'matches',
  selectSeason(id){context.selectedSeasonId=id;},
  renderTable(){},renderCards(){},renderSeasonsBar(){},renderSeasonDetails(){},renderTeamTournaments(){},renderSpecialTournaments(){},renderH2H(){},
};
context.location=context.window.location;
notices.tableSearch={value:''};notices.cardsSearch={value:''};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('    // Маршруты'),source.indexOf('    // HUD Strip')),context);
vm.runInContext('handleRouting()',context);
assert.deepEqual([...active],['tab-leaderboard']);
assert.equal(context.window.location.hash,'#/leaderboard');
context.window.location.hash='#/player/%';
assert.doesNotThrow(()=>vm.runInContext('handleRouting()',context));
assert.equal(context.window.location.hash,'#/leaderboard');
context.window.location.hash='#/team/team_1?view=tables&pair=A%20%26%20B';
vm.runInContext('handleRouting()',context);
assert.deepEqual([...active],['tab-teams']);
assert.equal(context.teamPairFilter,'A & B');
assert.equal(context.teamSubTab,'tables');
context.window.location.hash='#/special/cup_1?player=Kunio';
vm.runInContext('handleRouting()',context);
assert.deepEqual([...active],['tab-special']);
assert.equal(context.specialPlayerFilter,'Kunio');
context.window.location.hash='#/season/4';
vm.runInContext('handleRouting()',context);
assert.deepEqual([...active],['tab-seasons']);
assert.equal(context.selectedSeasonId,'4');
context.selectSeason=()=>{throw Error('Нельзя сбрасывать фильтры текущего сезона');};
assert.doesNotThrow(()=>vm.runInContext('handleRouting()',context));
assert.equal(vm.runInContext('escapeHTML("<script>\\\"&")',context),'&lt;script&gt;&quot;&amp;');
console.log('Маршруты, повреждённые ссылки, сохранение сезона и экранирование: OK');
vm.runInContext(source.slice(source.indexOf('    function teamTournamentMatches'),
                            source.indexOf('    function renderTeamTournamentDetails')),context);
assert.equal(vm.runInContext('teamTournamentMatches({playoff_matches:[{score:"6:2"}]}).length',context),1);
assert.equal(vm.runInContext('teamTournamentMatches({matches:[],playoff_matches:[{},{}]}).length',context),2);
assert.equal(vm.runInContext('isTeamPlayoffMatch({stage:"Групповой этап"})',context),false);
assert.equal(vm.runInContext('isTeamPlayoffMatch({stage:"1/2 финала"})',context),true);
assert.equal(vm.runInContext('isTeamPlayoffMatch({tour:"За 3-е место"})',context),true);
