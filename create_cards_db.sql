create table ActivatableAbility(card_id, cost, effect, energy_ability);
create table CardTypes(card_id, name);
create table CardSubtypes(card_id, name);
create table RuleCard(id, name, cost, token, strength, toughness);

insert into RuleCard values (101, 'Firesource', NULL, 0, NULL, NULL);
insert into CardTypes values (101, 'source');
insert into CardTypes values (101, 'basic');
insert into CardSubtypes values (101, 'firesource');
insert into ActivatableAbility values (101, '{T}', 'add_energy $controller {R}', 1);

insert into RuleCard values(102, 'Goblin Raiders', '{R}', 0, 1, 1);
insert into CardTypes values(102, 'creature');
insert into CardSubtypes values (102, 'goblin');
