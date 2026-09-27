function summary = validate_reference(projectRoot)
% Independent calculation for the bundled synthetic reference specimen.
if nargin < 1
    projectRoot = fileparts(fileparts(mfilename('fullpath')));
end
inputFile = fullfile(projectRoot, 'data', 'reference.csv');
expectedFile = fullfile(projectRoot, 'matlab', 'python_reference.json');
T = readtable(inputFile);
expected = jsondecode(fileread(expectedFile));

A0 = 10; % mm^2
L0 = 50; % mm
stress = T.force_N / A0;
strain = T.extension_mm / L0;

loadDrop = find(stress(1:end-1) > 0.25*max(stress) & ...
                stress(2:end) < 0.5*stress(1:end-1)), 1, 'last');
assert(~isempty(loadDrop), 'No fracture candidate found in the reference.');
stress = stress(1:loadDrop);
strain = strain(1:loadDrop);
fitRows = strain >= expected.elastic_min & strain <= expected.elastic_max;
p = polyfit(strain(fitRows), stress(fitRows), 1);
E = p(1);
nuFit = polyfit(strain(fitRows), T.transverse_strain(find(fitRows)), 1);
nu = -nuFit(1);

[UTS, maxRow] = max(stress);
offset = E*(strain - 0.002) + p(2);
difference = stress - offset;
k = find(difference(1:end-1) >= 0 & difference(2:end) < 0 & ...
         strain(2:end) >= 0.002, 1);
assert(~isempty(k), 'Offset intersection not found.');
fraction = difference(k)/(difference(k)-difference(k+1));
Rp02 = stress(k) + fraction*(stress(k+1)-stress(k));
Ur = 250^2/(2*E);
Ut = trapz(strain, stress);
trueStrain = log(1+strain(1:maxRow));
trueStress = stress(1:maxRow).*(1+strain(1:maxRow));

names = ["E_GPa"; "proof_MPa"; "UTS_MPa"; "poisson"; ...
         "resilience_MJ_m3"; "toughness_MJ_m3"];
values = [E/1000; Rp02; UTS; nu; Ur; Ut];
pythonValues = zeros(size(values));
for i = 1:numel(names)
    pythonValues(i) = expected.metrics.(char(names(i)));
end
relativeError = abs(values-pythonValues)./max(abs(pythonValues),eps);
summary = table(names, values, pythonValues, relativeError, ...
    'VariableNames', {'Property','MATLAB','Python','RelativeError'});
assert(all(relativeError < 1e-6), 'MATLAB and Python results differ.');
disp(summary);

outputDir = fullfile(projectRoot, 'matlab', 'results');
if ~isfolder(outputDir), mkdir(outputDir); end
writetable(summary, fullfile(outputDir, 'validation.csv'));
fig = figure('Color', 'w', 'Name', 'Tensile reference validation');
tiledlayout(1,2);
nexttile;
plot(strain*100, stress, 'LineWidth', 1.8); grid on;
xlabel('Engineering strain (%)'); ylabel('Engineering stress (MPa)');
title('Synthetic reference');
nexttile;
plot(trueStrain, trueStress, 'LineWidth', 1.8); grid on;
xlabel('True strain'); ylabel('True stress (MPa)');
title('Before maximum load');
exportgraphics(fig, fullfile(outputDir, 'reference_validation.png'), 'Resolution', 180);
end
